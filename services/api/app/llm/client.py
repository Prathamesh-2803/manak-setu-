"""Minimal Gemini REST client (no extra deps, uses httpx).

generate_json returns a dict on success, None on any failure so callers
can fall back to heuristics and the demo never blocks on the LLM.
"""

from __future__ import annotations

import json
import logging

import httpx

from app.config import get_settings

log = logging.getLogger("manak-setu.llm")

# Verified working 2026-10-04 (2.5-flash retired for new keys, 3.8-flash overloaded).
MODELS = ["gemini-3.7-flash", "gemini-3.5-flash", "gemini-3.6-flash"]
_API = "https://generativelanguage.googleapis.com/v1beta/models"


def _call(model: str, key: str, system: str, user: str, timeout: float) -> dict:
    body = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"parts": [{"text": user}]}],
        "generationConfig": {"response_mime_type": "application/json", "temperature": 0.2},
    }
    r = httpx.post(
        f"{_API}/{model}:generateContent",
        headers={"x-goog-api-key": key},
        json=body,
        timeout=timeout,
    )
    r.raise_for_status()
    text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(text)


def generate_json(system: str, user: str, timeout: float = 40.0) -> dict | None:
    settings = get_settings()
    if not settings.gemini_api_key:
        log.warning("GEMINI_API_KEY not set, skipping LLM call")
        return None
    for model in MODELS:
        for attempt in (1, 2):
            try:
                return _call(model, settings.gemini_api_key, system, user, timeout)
            except Exception as e:  # network, quota, bad JSON -> next model
                log.warning("LLM %s attempt %d failed: %s", model, attempt, e)
    return None
