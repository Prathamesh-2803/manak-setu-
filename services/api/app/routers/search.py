from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.retrieval import search as run_search

router = APIRouter(prefix="/api/v1", tags=["search"])


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    limit: int = Field(default=10, ge=1, le=50)
    rerank: bool = True


class SearchHit(BaseModel):
    id: str
    designation: str | None = None
    title: str | None = None
    aspect: str | None = None
    group_name: str | None = None
    certification: str | None = None
    score: float
    rerank_score: float | None = None


class SearchResponse(BaseModel):
    query: str
    took_ms: int
    reranked: bool
    results: list[SearchHit]


@router.post("/search", response_model=SearchResponse)
def search(req: SearchRequest) -> SearchResponse:
    return SearchResponse(**run_search(req.query, limit=req.limit, rerank=req.rerank))
