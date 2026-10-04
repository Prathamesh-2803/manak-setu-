"""Spec Decomposer: messy tender text -> structured facts + sub-queries.

LLM first (Gemini JSON mode); heuristic fallback (glossary + templates)
so the pipeline never blocks on the LLM.
"""

from __future__ import annotations

import logging
import re

import yaml

from app.llm.client import generate_json
from app.paths import find_data

log = logging.getLogger("manak-setu.decompose")

_SYSTEM = (
    "You are a procurement-standards assistant for Indian government tenders. "
    "Read the buyer's request (any language, may be Hinglish) and respond with JSON only: "
    '{"understood": "<one-line English restatement>", "product": "<main product>", '
    '"material": "<material or empty>", "grade_size": "<grades/sizes or empty>", '
    '"quantity": "<qty or empty>", "use": "<intended use or empty>", '
    '"language": "<en|hi|hinglish>", '
    '"sub_queries": ["<product specification query>", "<test methods query>", '
    '"<safety/code query>", "<marking/packaging/sampling query>"]}'
)

_HINGLISH_CUES = {
    "chahiye", "wala", "wale", "wali", "ke", "liye", "ka", "ki", "aur", "hai",
    "mein", "main", "saria", "sariya", "bhawan", "nirman", "maal", "saman",
}

_GLOSSARY: list[dict] | None = None


def _load_glossary() -> list[dict]:
    global _GLOSSARY
    if _GLOSSARY is None:
        raw = yaml.safe_load(find_data("glossary.yaml").read_text(encoding="utf-8"))
        _GLOSSARY = raw.get("concepts", [])
    return _GLOSSARY


def detect_language(q: str) -> str:
    if re.search(r"[\u0900-\u097F]", q):
        return "hi"
    words = set(re.findall(r"[a-z]+", q.lower()))
    if words & _HINGLISH_CUES:
        return "hinglish"
    return "en"


def _heuristic(q: str) -> dict:
    lang = detect_language(q)
    ql = q.lower()
    hints: list[str] = []
    matched: list[str] = []
    for c in _load_glossary():
        terms = [*(c.get("terms_en", [])), *(c.get("terms_hi", [])),
                 *(c.get("terms_hinglish", []))]
        if any(re.search(rf"\b{re.escape(t.lower())}\b", ql) for t in terms if t):
            matched.append(c.get("display", c["id"]))
            hints.extend(c.get("is_hints", []))
    if matched:
        label = ", ".join(matched)
        subs = [
            q,
            f"{label} product specification",
            f"{label} test methods and sampling",
            f"{label} marking packaging installation safety",
        ]
    else:
        subs = [q, f"{q} specification", f"{q} test method sampling",
                f"{q} marking packaging installation"]
    return {
        "understood": q if not matched else f"{q}  (interpreted: {', '.join(matched)})",
        "product": matched[0] if matched else q[:80],
        "material": "", "grade_size": "", "quantity": "", "use": "",
        "language": lang, "sub_queries": subs[:4], "is_hints": hints,
        "decomposer": "heuristic",
    }


def decompose(query: str) -> dict:
    data = generate_json(_SYSTEM, f"Buyer request: {query}")
    if data and isinstance(data.get("sub_queries"), list) and data["sub_queries"]:
        data["sub_queries"] = [str(s) for s in data["sub_queries"]][:4]
        while len(data["sub_queries"]) < 4:
            data["sub_queries"].append(query)
        data.setdefault("language", detect_language(query))
        data.setdefault("understood", query)
        data["decomposer"] = "llm"
        data["is_hints"] = _heuristic(query).get("is_hints", [])
        return data
    log.warning("LLM decompose failed, using heuristic fallback")
    return _heuristic(query)
