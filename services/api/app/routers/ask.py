"""POST /api/v1/ask - the full Manak Setu pipeline in one call.

decompose -> hybrid retrieve (per sub-query, no rerank) -> dedupe pool ->
glossary-hint injection -> cross-encoder rerank (top of pool) ->
graph expansion -> postgres enrich -> version guard + certification oracle ->
hallucination guardrail -> clause.
"""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app import retrieval
from app.config import get_settings
from app.db import pg as db
from app.db import graph
from app.stages import certification, clause as clause_mod, decompose, guardrail, version_guard

log = logging.getLogger("manak-setu.ask")
router = APIRouter(prefix="/api/v1", tags=["ask"])

_POOL_PER_QUERY = 8
_RERANK_POOL = 15
_cache: dict[str, dict] = {}


class AskRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    limit: int = Field(default=6, ge=1, le=10)
    expand: int = Field(default=6, ge=0, le=12)


class CertInfo(BaseModel):
    mandatory: bool
    scheme: str | None = None
    qco_status: str | None = None
    implemented_on: str | None = None
    ministry: str | None = None
    source: str | None = None


class StandardCard(BaseModel):
    id: str | None = None
    designation: str
    year: str | None = None
    title: str | None = None
    aspect: str | None = None
    role: str | None = None
    score: float | None = None
    rerank_score: float | None = None
    status: str = "unknown"
    replaced_by: str | None = None
    certification: CertInfo
    iso_equivalent: str | None = None
    detail_url: str | None = None
    evidence: str | None = None
    source: str = "retrieval"


class AskResponse(BaseModel):
    query: str
    understood: str
    language: str
    decomposer: str
    results: list[StandardCard]
    allied: list[StandardCard]
    clause: str
    confidence: float
    warnings: list[str]
    cached: bool = False
    took_ms: int
    stages_ms: dict[str, int]


def _card(des: str, row: dict | None, base: dict, source: str) -> StandardCard | None:
    if not guardrail.is_valid(des):
        return None
    version = version_guard.resolve(des, {des: row} if row else {})
    cert = certification.lookup(des, row)
    return StandardCard(
        id=(row or {}).get("id") or base.get("id"),
        designation=des,
        year=(row or {}).get("year") or base.get("year"),
        title=(row or {}).get("title") or base.get("title"),
        aspect=(row or {}).get("aspect") or base.get("aspect"),
        role=(row or {}).get("aspect") or base.get("aspect"),
        score=base.get("score"),
        rerank_score=base.get("rerank_score"),
        status=version["status"],
        replaced_by=version["replaced_by"],
        certification=CertInfo(**cert),
        iso_equivalent=(row or {}).get("iso_equivalent"),
        detail_url=(row or {}).get("detail_url"),
        evidence=(row or {}).get("title") or base.get("title"),
        source=source,
    )


def _run(req: AskRequest) -> dict:
    t0 = time.perf_counter()
    stages_ms: dict[str, int] = {}
    warnings: list[str] = []

    def mark(name: str, t: float) -> None:
        stages_ms[name] = int((time.perf_counter() - t) * 1000)

    t = time.perf_counter()
    dec = decompose.decompose(req.query)
    mark("decompose", t)

    t = time.perf_counter()
    pool: list[dict] = []
    seen: set[str] = set()
    # Sequential: concurrent BGE-M3 encodes thrash CPU and end up slower.
    for sq in dec.get("sub_queries", [req.query]):
        try:
            hits = retrieval.search(sq, limit=_POOL_PER_QUERY, rerank=False)["results"]
        except Exception as e:
            log.warning("sub-query retrieval failed: %s", e)
            continue
        for h in hits:
            des = (h.get("designation") or "").strip()
            if des and des not in seen:
                seen.add(des)
                pool.append(h)
    if not pool:
        warnings.append("Retrieval hiccup on sub-queries; results may be incomplete.")
    mark("retrieve", t)

    # Glossary hints: force-include known product standards the retriever may miss.
    t = time.perf_counter()
    hint_rows: dict[str, dict] = {}
    for hint in dec.get("is_hints", [])[:5]:
        if hint not in seen:
            seen.add(hint)
            fetched = db.fetch_by_designations([hint])
            if fetched:
                hint_rows.update(fetched)
                pool.insert(0, {"designation": hint, "score": None,
                                "rerank_score": None, "_hint": True})
    mark("hints", t)

    t = time.perf_counter()
    cand = pool[:_RERANK_POOL]
    # Rerank with the English restatement: cross-lingual (Hinglish) raw
    # queries score near-zero, the LLM "understood" text separates well.
    rerank_q = dec.get("understood") or req.query
    texts = [f"{c.get('designation') or ''} {(hint_rows.get(c['designation'], {}) or {}).get('title') or c.get('title') or ''}" for c in cand]
    try:
        scores = retrieval.rerank(rerank_q, texts)
    except Exception as e:
        log.warning("rerank failed: %s", e)
        warnings.append("Reranker unavailable; results are in fusion order.")
        scores = [0.0] * len(cand)
    for c, s in zip(cand, scores):
        c["rerank_score"] = s
    # Pure score order: glossary hints only guarantee recall, ranking decides.
    cand.sort(key=lambda c: -(c["rerank_score"] if c["rerank_score"] is not None else -1e9))
    ordered = cand + [c for c in pool[_RERANK_POOL:] if c not in cand]
    for c in pool[_RERANK_POOL:]:
        if "rerank_score" not in c:
            c["rerank_score"] = None
    mark("rerank", t)

    t = time.perf_counter()
    # Seeds: top hit + product specs (codes/test-methods alone seed poorly).
    seeds: list[str] = []
    for c in ordered:
        des = c.get("designation")
        if not des or des in seeds:
            continue
        if not seeds or (c.get("aspect") or "") == "Product Specification":
            seeds.append(des)
        if len(seeds) >= 3:
            break
    allied_raw = graph.expand(seeds, per_seed=req.expand) if req.expand else []
    mark("graph", t)

    t = time.perf_counter()
    all_des = [c["designation"] for c in ordered if c.get("designation")]
    all_des += [a.get("designation") for a in allied_raw if a.get("designation")]
    rows = db.fetch_by_designations(list(dict.fromkeys(all_des)))
    result_cards: list[StandardCard] = []
    dropped = 0
    for c in ordered:
        card = _card(c["designation"], rows.get(c["designation"]), c, "retrieval")
        if card:
            result_cards.append(card)
        else:
            dropped += 1
        if len(result_cards) >= req.limit:
            break
    main_cores = {guardrail.core(c.designation) for c in result_cards}
    allied_cards: list[StandardCard] = []
    for a in allied_raw:
        if guardrail.core(a.get("designation")) in main_cores:
            continue
        card = _card(a["designation"], rows.get(a["designation"]), a, "graph")
        if card:
            allied_cards.append(card)
        else:
            dropped += 1
        if len(allied_cards) >= 8:
            break
    mark("enrich_guard", t)

    if dropped > 0:
        warnings.append(f"Guardrail removed {dropped} unverifiable reference(s).")
    for c in [*result_cards, *allied_cards]:
        if c.status != "current":
            warnings.append(f"{c.designation}: {c.status}"
                            + (f" -> {c.replaced_by}" if c.replaced_by else ""))

    rr = [c.rerank_score for c in result_cards if c.rerank_score is not None]
    confidence = guardrail.confidence_from_scores(rr)
    if confidence < get_settings().confidence_threshold:
        warnings.append("Low confidence - please verify with a BIS expert.")
    if dec.get("decomposer") == "heuristic":
        warnings.append("LLM decomposer unavailable; used keyword fallback.")

    main = result_cards[0] if result_cards else None
    clause_text = ""
    if main:
        mrow = rows.get(main.designation, {})
        clause_text = clause_mod.build_clause(
            {"designation": main.designation, "year": main.year, "title": main.title},
            main.certification.model_dump(), {"status": main.status,
                                              "replaced_by": main.replaced_by})

    took_ms = int((time.perf_counter() - t0) * 1000)
    return {
        "query": req.query,
        "understood": dec.get("understood", req.query),
        "language": dec.get("language", "en"),
        "decomposer": dec.get("decomposer", "heuristic"),
        "results": [c.model_dump() for c in result_cards],
        "allied": [c.model_dump() for c in allied_cards],
        "clause": clause_text,
        "confidence": confidence,
        "warnings": warnings,
        "took_ms": took_ms,
        "stages_ms": stages_ms,
    }


@router.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    key = f"{req.query.strip().lower()}|{req.limit}|{req.expand}"
    if key in _cache:
        out = dict(_cache[key])
        out["cached"] = True
        return AskResponse(**out)
    out = _run(req)
    _cache[key] = out
    if len(_cache) > 200:
        _cache.clear()
    return AskResponse(**out)
