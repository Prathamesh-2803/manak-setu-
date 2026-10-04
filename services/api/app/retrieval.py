"""Hybrid retrieval: Qdrant BM25-sparse + BGE-M3-dense fused with RRF,
optional cross-encoder rerank (BAAI/bge-reranker-v2-m3).

All heavy resources (model, client, meta) are lazy singletons so the API
starts fast and only pays the model cost on first search.
"""

from __future__ import annotations

import json
import pathlib
import threading
import time

from qdrant_client import QdrantClient, models

from app.config import get_settings
from app.text_utils import bm25_query_weights

_settings = get_settings()

_client: QdrantClient | None = None
_meta: dict | None = None
_embedder = None
_reranker = None
_lock = threading.Lock()


def _find_meta() -> pathlib.Path:
    p = pathlib.Path(_settings.index_meta_path)
    if p.exists():
        return p
    for base in (pathlib.Path.cwd(), *pathlib.Path.cwd().parents):
        candidate = base / "data" / "index_meta.json"
        if candidate.exists():
            return candidate
    return p


def get_client() -> QdrantClient:
    global _client
    with _lock:
        if _client is None:
            _client = QdrantClient(
                url=_settings.qdrant_url, timeout=60, check_compatibility=False
            )
        return _client


def _reset_client() -> None:
    global _client
    with _lock:
        if _client is not None:
            try:
                _client.close()
            except Exception:
                pass
            _client = None


def load_meta() -> dict:
    global _meta
    with _lock:
        if _meta is None:
            _meta = json.loads(_find_meta().read_text(encoding="utf-8"))
        return _meta


def _get_embedder():
    global _embedder
    with _lock:
        if _embedder is None:
            from sentence_transformers import SentenceTransformer

            # fp16 halves RAM (~2.3 GB -> ~1.2 GB); negligible recall impact.
            try:
                import torch

                _embedder = SentenceTransformer(
                    _settings.embedding_model,
                    model_kwargs={"torch_dtype": torch.float16},
                )
            except Exception:
                _embedder = SentenceTransformer(_settings.embedding_model)
        return _embedder


def _get_reranker():
    global _reranker
    with _lock:
        if _reranker is None:
            from sentence_transformers import CrossEncoder

            _reranker = CrossEncoder(_settings.rerank_model)
        return _reranker


def rerank(query: str, texts: list[str]) -> list[float]:
    """Score (query, text) pairs with the cross-encoder. Used to order pools."""
    if not texts:
        return []
    scores = _get_reranker().predict([(query, t) for t in texts])
    return [float(s) for s in scores]


def _query(collection: str, prefetch: list, fusion_limit: int):
    return get_client().query_points(
        collection_name=collection,
        prefetch=prefetch,
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=fusion_limit,
        with_payload=True,
    )


def search(query: str, limit: int = 10, rerank: bool = True) -> dict:
    t0 = time.perf_counter()
    meta = load_meta()
    collection = meta["collection"]

    prefetch: list[models.Prefetch] = []
    k = _settings.rerank_top_k if rerank else limit
    sp_indices, sp_values = bm25_query_weights(query, meta["terms"], meta["idf"])
    if sp_indices:
        prefetch.append(
            models.Prefetch(
                query=models.SparseVector(indices=sp_indices, values=sp_values),
                using="sparse",
                limit=k,
            )
        )

    dense = (
        _get_embedder()
        .encode([query], normalize_embeddings=True, convert_to_numpy=True)[0]
        .tolist()
    )
    prefetch.append(models.Prefetch(query=dense, using="dense", limit=k))

    fusion_limit = _settings.rerank_top_k if rerank else limit
    try:
        response = _query(collection, prefetch, fusion_limit)
    except Exception:
        _reset_client()  # stale pooled connection (Docker NAT flake) -> retry once
        response = _query(collection, prefetch, fusion_limit)
    hits = response.points

    results = []
    for h in hits:
        p = h.payload or {}
        results.append(
            {
                "id": str(p.get("id")),
                "designation": p.get("designation"),
                "title": p.get("title"),
                "aspect": p.get("aspect"),
                "group_name": p.get("group_name"),
                "certification": p.get("certification"),
                "score": float(h.score),
                "rerank_score": None,
            }
        )

    if rerank and results:
        pairs = [(query, f"{r['designation'] or ''} {r['title'] or ''}") for r in results]
        scores = _get_reranker().predict(pairs)
        for r, s in zip(results, scores):
            r["rerank_score"] = float(s)
        results.sort(key=lambda r: r["rerank_score"], reverse=True)

    results = results[:limit]
    took_ms = int((time.perf_counter() - t0) * 1000)
    return {
        "query": query,
        "took_ms": took_ms,
        "reranked": rerank and len(results) > 0,
        "results": results,
    }
