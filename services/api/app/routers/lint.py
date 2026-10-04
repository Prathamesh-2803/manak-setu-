"""POST /api/v1/lint - Tender Linter (compliance audit engine).

Paste a draft tender -> health report:
- outdated IS references (withdrawn -> replacement, via Version Guard)
- foreign specs without Indian equivalent (GFR 2017 Rule 144(iii) flag)
- missing allied standards (ask pipeline top picks not mentioned in text)
- health score 0-100 + verdict.
"""

from __future__ import annotations

import logging
import re
import time

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.db import pg as db
from app.routers.ask import AskRequest, _run
from app.stages import guardrail, version_guard

log = logging.getLogger("manak-setu.lint")
router = APIRouter(prefix="/api/v1", tags=["lint"])

_IS_RE = re.compile(r"\bIS\s*(\d+)\s*(?::\s*(\d{4}))?", re.IGNORECASE)
_FOREIGN_RE = re.compile(r"\b(IEC|EN|ISO|ASTM|DIN|BS|JIS)\s*\d[\d\s\-/():A-Za-z]*", re.IGNORECASE)


class LintRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=12000)


class Finding(BaseModel):
    kind: str  # outdated | missing | foreign | ok
    severity: str  # high | medium | low | info
    title: str
    detail: str
    suggestion: str | None = None


class LintResponse(BaseModel):
    score: int
    verdict: str
    findings: list[Finding]
    checked_is: list[str]
    took_ms: int


def _verdict(score: int) -> str:
    if score >= 85:
        return "Bid-ready — no blocking issues found."
    if score >= 60:
        return "Needs work — fix the flagged clauses before publishing."
    return "High risk — outdated or foreign references must be resolved."


@router.post("/lint", response_model=LintResponse)
def lint(req: LintRequest) -> LintResponse:
    t0 = time.perf_counter()
    findings: list[Finding] = []
    score = 100

    # 1. Outdated IS references mentioned in the text.
    mentioned = [f"IS {m.group(1)}" for m in _IS_RE.finditer(req.text)]
    mentioned = list(dict.fromkeys(mentioned))[:20]
    rows = db.fetch_by_designations(mentioned)
    for des in mentioned:
        row = rows.get(des)
        # resolve() works even when the old row itself isn't in our DB
        # (successor lookup finds who replaced it).
        v = version_guard.resolve(des, {des: row} if row else {})
        if v["status"] != "current" and v.get("replaced_by"):
            score -= 25
            quoted = f"{row.get('designation')}:{row.get('year')}" if row and row.get("year") else des
            findings.append(Finding(
                kind="outdated", severity="high",
                title=f"{quoted} is {v['status']} — use {v['replaced_by']}",
                detail=f"The tender quotes {des}, but BIS lists "
                       f"{v['replaced_by']} as the replacement.",
                suggestion=f"Replace with {v['replaced_by']} (latest revision including amendments).",
            ))

    # 2. Foreign specs (GFR 2017 Rule 144(iii) flag).
    foreign = list(dict.fromkeys(m.group(0).strip() for m in _FOREIGN_RE.finditer(req.text)))[:10]
    for f in foreign:
        score -= 15
        findings.append(Finding(
            kind="foreign", severity="medium",
            title=f"Foreign specification: {f}",
            detail="GFR 2017 Rule 144(iii): prefer national standards where they exist; "
                   "reasons for a foreign spec must be recorded in writing.",
            suggestion="Map to the Indian equivalent via Manak Setu search, or record written reasons.",
        ))

    # 3. Missing allied standards: ask-pipeline top picks not mentioned.
    try:
        recs = _run(AskRequest(query=req.text[:2000], limit=6, expand=0))
        mentioned_cores = {guardrail.core(d) for d in mentioned}
        added = 0
        for c in recs["results"]:
            if guardrail.core(c["designation"]) not in mentioned_cores and added < 3:
                added += 1
                score -= 10
                findings.append(Finding(
                    kind="missing", severity="medium",
                    title=f"Missing allied standard: {c['designation']}",
                    detail=f"{c['title'] or ''} ({c['aspect'] or 'related standard'}) "
                           f"is normally cited alongside this procurement.",
                    suggestion=f"Consider adding {c['designation']}"
                               f"{':' + c['year'] if c.get('year') else ''} to the technical specs.",
                ))
    except Exception as e:
        log.warning("lint recommendation pass failed: %s", e)

    if not findings:
        findings.append(Finding(
            kind="ok", severity="info",
            title="No issues found",
            detail=f"Checked {len(mentioned)} IS reference(s); all current, no foreign specs, no gaps detected.",
            suggestion=None,
        ))

    score = max(0, min(100, score))
    return LintResponse(
        score=score, verdict=_verdict(score), findings=findings,
        checked_is=mentioned, took_ms=int((time.perf_counter() - t0) * 1000),
    )
