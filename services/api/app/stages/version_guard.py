"""Version Guard: resolve each designation to its current status.

BIS data semantics (verified 2026-10-04): a row's `superseding_is` names its
PREDECESSORS, i.e. row R supersedes them (e.g. IS 1786:2008 supersedes
IS 1139:1966). So D is current unless some *other* row names D as its
predecessor. 'None'/empty -> current. Successor missing from DB ->
superseded_unverified (never invent a number).
"""

from __future__ import annotations

import re

from app.db import pg as db

_CORE_RE = re.compile(r"IS\s*\d+", re.IGNORECASE)


def core(designation: str | None) -> str:
    m = re.search(r"IS\s*(\d+)", designation or "", re.IGNORECASE)
    return m.group(1) if m else ""


def _successors(designation: str) -> list[dict]:
    """Rows that name `designation` as a predecessor, newest first."""
    c = core(designation)
    if not c:
        return []
    rows = db.query(
        "SELECT designation, year FROM standards "
        "WHERE superseding_is ~ ('\\m' || %s || '\\M') "
        "AND regexp_replace(designation, '[^0-9]', '', 'g') != %s "
        "ORDER BY year DESC NULLS LAST",
        (c, c),
    )
    return rows


def resolve(designation: str, rows: dict[str, dict]) -> dict:
    seen = [designation]
    current = designation
    for _ in range(3):
        succ = _successors(current)
        if not succ:
            break
        nxt = succ[0]["designation"]
        if not nxt or core(nxt) == core(current) or nxt in seen:
            break
        seen.append(nxt)
        current = nxt
    if len(seen) == 1:
        return {"status": "current", "replaced_by": None, "replaced_by_year": None,
                "note": None}
    final = seen[-1]
    final_row = rows.get(final) or db.fetch_by_designations([final]).get(final)
    if final_row:
        rows[final] = final_row
        return {"status": "withdrawn", "replaced_by": final_row.get("designation", final),
                "replaced_by_year": final_row.get("year"),
                "note": f"Withdrawn/superseded; use {final_row.get('designation', final)}"}
    return {"status": "superseded_unverified", "replaced_by": final,
            "replaced_by_year": None,
            "note": f"BIS lists {final} as replacement but it is not in our database"}
