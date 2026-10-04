"""GET /api/v1/map - Foreign-to-Indian standard mapper.

Input like 'IEC 60335' or 'ISO 11611' -> Indian Standards whose BIS record
lists that code as Identical/Equivalent. Pure DB lookup, no LLM.
Unofficial guesses are never returned: empty means 'ask a BIS expert'.
"""

from __future__ import annotations

import logging
import re

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.db import pg as db

log = logging.getLogger("manak-setu.map")
router = APIRouter(prefix="/api/v1", tags=["map"])


class MapHit(BaseModel):
    designation: str
    year: str | None = None
    title: str | None = None
    iso_equivalent: str | None = None
    certification: str | None = None


class MapResponse(BaseModel):
    query: str
    normalized: str
    matches: list[MapHit]
    note: str | None = None


def _core(raw: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", raw or "").upper()


@router.get("/map", response_model=MapResponse)
def map_foreign(foreign: str = Query(..., min_length=3, max_length=60)) -> MapResponse:
    core = _core(foreign)
    if len(core) < 4:
        return MapResponse(query=foreign, normalized=core, matches=[],
                           note="Code too short to map reliably.")
    try:
        rows = db.query(
            "SELECT designation, year, title, iso_equivalent, certification "
            "FROM standards "
            "WHERE iso_equivalent IS NOT NULL AND "
            "REPLACE(REPLACE(UPPER(iso_equivalent), ' ', ''), ':', '') LIKE %s "
            "ORDER BY year DESC NULLS LAST LIMIT 10",
            (f"%{core}%",),
        )
    except Exception as e:
        log.warning("map query failed: %s", e)
        rows = []
    hits = [MapHit(**{k: r.get(k) for k in
                      ("designation", "year", "title", "iso_equivalent", "certification")})
            for r in rows]
    note = (None if hits else
            "No official BIS-recorded equivalent in our database — suggested mappings need expert review.")
    return MapResponse(query=foreign, normalized=core, matches=hits, note=note)
