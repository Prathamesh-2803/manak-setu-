"""Neo4j access via the HTTP transactional API (no extra driver dep).

NEO4J_URL is bolt://host:7687 -> translated to http://host:7474.
"""

from __future__ import annotations

import logging
import re
import threading

import httpx

from app.config import get_settings

log = logging.getLogger("manak-setu.graph")

_graph_cores: set[str] | None = None
_lock = threading.Lock()


def _http_base() -> tuple[str, tuple[str, str]]:
    s = get_settings()
    base = s.neo4j_url.replace("bolt://", "http://").replace(":7687", ":7474")
    return f"{base}/db/neo4j/tx/commit", (s.neo4j_user, s.neo4j_password)


def cypher(statement: str, parameters: dict | None = None, timeout: float = 20.0) -> list[dict] | None:
    url, auth = _http_base()
    try:
        r = httpx.post(
            url, auth=auth,
            json={"statements": [{"statement": statement, "parameters": parameters or {}}]},
            timeout=timeout,
        )
        r.raise_for_status()
        body = r.json()
        if body.get("errors"):
            log.warning("cypher errors: %s", body["errors"][:1])
            return None
        res = body["results"][0]
        out = []
        for item in res.get("data", []):
            vals = item.get("row") if isinstance(item, dict) else item
            out.append(dict(zip(res["columns"], vals)))
        return out
    except Exception as e:
        log.warning("neo4j http failed: %s", e)
        return None


def expand(seeds: list[str], per_seed: int = 6) -> list[dict]:
    """REFERS_TO neighbours of seed designations.

    Fast path first: exact designation match (0.3 s). Seeds with no exact
    node (e.g. year-suffixed graph nodes) fall back to prefix match.
    """
    seeds = [s for s in seeds if s]
    if not seeds:
        return []
    limit = per_seed * len(seeds)
    rows = cypher(
        "MATCH (a:Standard)-[:REFERS_TO]->(b:Standard) "
        "WHERE a.designation IN $seeds AND b.designation IS NOT NULL "
        "RETURN DISTINCT b.designation AS designation, b.title AS title, "
        "  b.aspect AS aspect, b.year AS year, b.certification AS certification, "
        "  count(*) AS refs ORDER BY refs DESC LIMIT $limit",
        {"seeds": seeds, "limit": limit},
    ) or []
    matched = {r["s"] for r in (cypher(
        "MATCH (a:Standard)-[:REFERS_TO]->() WHERE a.designation IN $seeds "
        "RETURN DISTINCT a.designation AS s", {"seeds": seeds}) or [])}
    missing = [s for s in seeds if s not in matched]
    if missing:
        extra = cypher(
            "MATCH (a:Standard)-[:REFERS_TO]->(b:Standard) "
            "WHERE ANY(s IN $seeds WHERE b.designation IS NOT NULL AND "
            "  (a.designation STARTS WITH s + ' ' "
            "   OR a.designation STARTS WITH s + ':')) "
            "RETURN DISTINCT b.designation AS designation, b.title AS title, "
            "  b.aspect AS aspect, b.year AS year, b.certification AS certification, "
            "  count(*) AS refs ORDER BY refs DESC LIMIT $limit",
            {"seeds": missing, "limit": limit},
        ) or []
        seen = {r.get("designation") for r in rows}
        for r in extra:
            if r.get("designation") not in seen:
                seen.add(r["designation"])
                rows.append(r)
    return rows


def all_cores() -> set[str]:
    global _graph_cores
    with _lock:
        if _graph_cores is None:
            rows = cypher("MATCH (n:Standard) WHERE n.designation IS NOT NULL "
                          "RETURN DISTINCT n.designation AS d") or []
            cores = set()
            for r in rows:
                m = re.search(r"IS\s*(\d+)", r["d"] or "", re.IGNORECASE)
                if m:
                    cores.add(m.group(1))
            _graph_cores = cores
        return _graph_cores
