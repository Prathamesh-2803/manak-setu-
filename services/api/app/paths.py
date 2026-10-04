"""Resolve repo data files whether running from repo root, services/api, or container."""

from __future__ import annotations

import pathlib


def find_data(name: str) -> pathlib.Path:
    p = pathlib.Path("data") / name
    if p.exists():
        return p
    for base in (pathlib.Path.cwd(), *pathlib.Path.cwd().parents):
        candidate = base / "data" / name
        if candidate.exists():
            return candidate
    return p  # caller gets a clear FileNotFoundError
