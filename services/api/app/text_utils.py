"""Shared text utilities used by both the indexer (pipeline/) and the API.

Index-time and query-time MUST use identical tokenization and BM25 weighting,
otherwise sparse retrieval silently degrades.
"""

from __future__ import annotations

import re
from functools import lru_cache

STOPWORDS = frozenset(
    """
    a an and are as at be been but by for from had has have he her his how i if in into is it its
    me my no not of on or our she so that the their them then there these they this to too up us
    was we were what when where which who whom why will with you your
    """.split()
)

_TOKEN_RE = re.compile(r"[a-z0-9]+")


@lru_cache(maxsize=1)
def _stemmer():
    from py_rust_stemmers import SnowballStemmer

    return SnowballStemmer("english")


def tokenize(text: str) -> list[str]:
    if not text:
        return []
    stem = _stemmer().stem_word
    out = []
    for tok in _TOKEN_RE.findall(text.lower()):
        if len(tok) <= 1 or tok in STOPWORDS:
            continue
        out.append(stem(tok))
    return out


def bm25_query_weights(
    query: str,
    terms: list[str],
    idf: list[float],
) -> tuple[list[int], list[float]]:
    """Map a free-text query onto the index vocabulary.

    Returns (indices, values) for Qdrant's sparse vector. Unseen terms are
    dropped; term frequency in the query scales the idf weight.
    """
    vocab = {t: i for i, t in enumerate(terms)}
    counts: dict[int, int] = {}
    for tok in tokenize(query):
        i = vocab.get(tok)
        if i is not None:
            counts[i] = counts.get(i, 0) + 1
    if not counts:
        return [], []
    indices = sorted(counts)
    values = [float(idf[i] * counts[i]) for i in indices]
    return indices, values
