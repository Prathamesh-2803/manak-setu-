"""Index Indian Standards into Qdrant: dense (BGE-M3) + sparse (BM25 named vectors).

Creates/reuses the `standards` collection, writes data/index_meta.json
(vocabulary + idf) which the API's query-time sparse builder needs.

Usage:
  python pipeline/index_qdrant.py --limit 300   # smoke test
  python pipeline/index_qdrant.py --fresh       # full rebuild
  python pipeline/index_qdrant.py               # resume: index only missing ids
"""

from __future__ import annotations

import argparse
import collections
import json
import math
import os
import pathlib
import sys
import time
from datetime import date

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "services" / "api"))

from app.text_utils import tokenize  # noqa: E402  (path setup above is intentional)

import psycopg  # noqa: E402
from psycopg.rows import dict_row  # noqa: E402
from qdrant_client import QdrantClient, models  # noqa: E402

QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://manak:manak@localhost:5432/manak_setu")
META_PATH = pathlib.Path("data/index_meta.json")

COLLECTION = "standards"
MODEL_NAME = "BAAI/bge-m3"
DIMS = 1024
K1 = 1.2
B = 0.75
BATCH = 256
EMBED_BATCH = 32

PAYLOAD_FIELDS = [
    "id",
    "designation",
    "is_number_raw",
    "year",
    "title",
    "short_title",
    "aspect",
    "certification",
    "iso_equivalent",
    "tech_committee",
    "tech_department",
    "group_name",
]


def load_docs(limit: int | None) -> list[dict]:
    sql = "SELECT * FROM standards ORDER BY id"
    if limit:
        sql += f" LIMIT {int(limit)}"
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        return [dict(r) for r in conn.execute(sql).fetchall()]


def doc_text(r: dict) -> str:
    parts = [r.get("designation"), r.get("title"), r.get("short_title"), r.get("aspect"), r.get("group_name")]
    return " ".join(str(p) for p in parts if p)


def build_sparse(texts: list[str]) -> tuple[list[tuple[list[int], list[float]]], list[str], list[float], float]:
    token_lists = [tokenize(t) for t in texts]
    n = max(len(token_lists), 1)
    df: collections.Counter = collections.Counter()
    lengths = []
    for toks in token_lists:
        lengths.append(len(toks))
        df.update(set(toks))
    terms = sorted(df)
    vocab = {t: i for i, t in enumerate(terms)}
    idf = [math.log(1.0 + (n - df[t] + 0.5) / (df[t] + 0.5)) for t in terms]
    avgdl = (sum(lengths) / n) or 1.0

    out = []
    for toks in token_lists:
        tf = collections.Counter(toks)
        dl = len(toks) or 1
        idxs: list[int] = []
        vals: list[float] = []
        for t, f in tf.items():
            i = vocab[t]
            w = idf[i] * (f * (K1 + 1.0)) / (f + K1 * (1.0 - B + B * dl / avgdl))
            idxs.append(i)
            vals.append(float(w))
        order = sorted(range(len(idxs)), key=lambda k: idxs[k])
        out.append(([idxs[k] for k in order], [vals[k] for k in order]))
    return out, terms, idf, avgdl


def encode_dense(texts: list[str]):
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MODEL_NAME)
    return model.encode(
        texts,
        batch_size=EMBED_BATCH,
        normalize_embeddings=True,
        show_progress_bar=True,
        convert_to_numpy=True,
    )


def ensure_collection(client: QdrantClient) -> None:
    if client.collection_exists(COLLECTION):
        return
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config={"dense": models.VectorParams(size=DIMS, distance=models.Distance.COSINE)},
        sparse_vectors_config={"sparse": models.SparseVectorParams()},
    )
    print(f"[index] created collection {COLLECTION!r}")


def existing_ids(client: QdrantClient) -> set[int]:
    if not client.collection_exists(COLLECTION):
        return set()
    have: set[int] = set()
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=COLLECTION, limit=1000, offset=offset, with_payload=False, with_vectors=False
        )
        have.update(p.id for p in points)
        if offset is None:
            break
    return have


def write_meta(terms: list[str], idf: list[float], avgdl: float, n_docs: int) -> None:
    META_PATH.parent.mkdir(parents=True, exist_ok=True)
    META_PATH.write_text(
        json.dumps(
            {
                "model": MODEL_NAME,
                "dims": DIMS,
                "collection": COLLECTION,
                "k1": K1,
                "b": B,
                "avgdl": avgdl,
                "n_docs": n_docs,
                "generated": date.today().isoformat(),
                "terms": terms,
                "idf": idf,
            }
        ),
        encoding="utf-8",
    )
    print(f"[index] wrote {META_PATH} ({len(terms)} terms)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="index only first N docs (smoke test)")
    ap.add_argument("--fresh", action="store_true", help="drop and rebuild the collection")
    ap.add_argument("--skip-embed", action="store_true", help="sparse only (debug)")
    args = ap.parse_args()

    t0 = time.time()
    docs = load_docs(args.limit or None)
    print(f"[index] loaded {len(docs)} docs from postgres")

    texts = [doc_text(r) for r in docs]
    sparse_all, terms, idf, avgdl = build_sparse(texts)
    write_meta(terms, idf, avgdl, len(docs))

    client = QdrantClient(url=QDRANT_URL)
    if args.fresh and client.collection_exists(COLLECTION):
        client.delete_collection(COLLECTION)
        print(f"[index] dropped collection {COLLECTION!r}")
    ensure_collection(client)

    have = existing_ids(client)
    todo_idx = [i for i, r in enumerate(docs) if int(r["id"]) not in have]
    print(f"[index] already have {len(have)}, to index: {len(todo_idx)}")
    if not todo_idx:
        print("[index] nothing to do")
        return

    todo_docs = [docs[i] for i in todo_idx]
    todo_sparse = [sparse_all[i] for i in todo_idx]
    todo_texts = [texts[i] for i in todo_idx]

    dense = None
    if not args.skip_embed:
        print(f"[index] encoding {len(todo_texts)} docs with {MODEL_NAME} (CPU, this takes a while)...")
        dense = encode_dense(todo_texts)

    points = []
    for j, (r, (sp_i, sp_v)) in enumerate(zip(todo_docs, todo_sparse)):
        vector: dict = {"sparse": models.SparseVector(indices=sp_i, values=sp_v)}
        if dense is not None:
            vector["dense"] = dense[j].tolist()
        else:
            vector["dense"] = [0.0] * DIMS
        points.append(
            models.PointStruct(
                id=int(r["id"]),
                vector=vector,
                payload={k: r.get(k) for k in PAYLOAD_FIELDS},
            )
        )
        if len(points) >= BATCH:
            client.upsert(collection_name=COLLECTION, points=points, wait=True)
            points = []
    if points:
        client.upsert(collection_name=COLLECTION, points=points, wait=True)

    count = client.count(collection_name=COLLECTION, exact=True).count
    print(f"[index] collection count: {count} (expected {len(docs)})")
    print(f"[index] done in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
