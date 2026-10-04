"""Hallucination guardrail: only DB-known IS numbers may appear in output.

Validity = numeric core present in Postgres designations or Neo4j nodes.
"""

from __future__ import annotations

import re

from app.db import pg as db
from app.db import graph


def core(designation: str | None) -> str:
    """First IS number group only: 'IS 1403 : PART 1' -> '1403' (not '14031')."""
    m = re.search(r"IS\s*(\d+)", designation or "", re.IGNORECASE)
    return m.group(1) if m else ""


def is_valid(designation: str | None) -> bool:
    c = core(designation)
    if not c:
        return False
    try:
        if c in db.valid_cores():
            return True
    except Exception:
        pass
    try:
        return c in graph.all_cores()
    except Exception:
        return False


def confidence_from_scores(scores: list[float]) -> float:
    if not scores:
        return 0.5
    lo, hi = min(scores), max(scores)
    top = scores[0]
    norm = (top - lo) / (hi - lo + 1e-6)
    return round(min(0.95, max(0.40, 0.55 + 0.40 * norm)), 2)
