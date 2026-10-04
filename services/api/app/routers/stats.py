"""GET /api/v1/stats - live dataset counters for the UI (never hardcoded)."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel

from app import retrieval
from app.db import pg as db
from app.db import graph

log = logging.getLogger("manak-setu.stats")
router = APIRouter(prefix="/api/v1", tags=["stats"])


class StatsResponse(BaseModel):
    standards: int
    qco_tracked: int
    graph_nodes: int
    graph_edges: int
    fake_is: int = 0


@router.get("/stats", response_model=StatsResponse)
def stats() -> StatsResponse:
    try:
        n_std = db.query("SELECT COUNT(*) AS c FROM standards")[0]["c"]
    except Exception as e:
        log.warning("stats standards failed: %s", e)
        n_std = 0
    try:
        n_qco = len(db.qco_snapshot())
    except Exception as e:
        log.warning("stats qco failed: %s", e)
        n_qco = 0
    nodes, edges = 0, 0
    try:
        r = graph.cypher(
            "MATCH (n:Standard) OPTIONAL MATCH (n)-[r:REFERS_TO]->() "
            "RETURN count(DISTINCT n) AS nodes, count(r) AS edges")
        if r:
            nodes, edges = int(r[0].get("nodes") or 0), int(r[0].get("edges") or 0)
    except Exception as e:
        log.warning("stats graph failed: %s", e)
    try:
        n_vec = retrieval.get_client().get_collection(
            retrieval.load_meta()["collection"]).points_count or 0
    except Exception as e:
        log.warning("stats qdrant failed: %s", e)
        n_vec = 0
    return StatsResponse(
        standards=n_vec or n_std, qco_tracked=n_qco,
        graph_nodes=nodes, graph_edges=edges,
    )
