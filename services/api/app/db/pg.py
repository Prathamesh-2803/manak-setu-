"""Postgres access + QCO snapshot (Certification Oracle data)."""

from __future__ import annotations

import re
import threading

import psycopg
import yaml
from psycopg.rows import dict_row

from app.config import get_settings
from app.paths import find_data

_COLS = (
    "id, designation, is_number_raw, year, title, short_title, aspect, "
    "certification, superseding_is, iso_equivalent, tech_committee, "
    "tech_department, group_name, detail_url"
)

_qco: dict | None = None
_qco_lock = threading.Lock()
_valid_cores: set[str] | None = None


def _connect():
    return psycopg.connect(get_settings().database_url, row_factory=dict_row)


def query(sql: str, params: tuple = ()) -> list[dict]:
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return list(cur.fetchall())


def _core(designation: str | None) -> str:
    m = re.search(r"IS\s*(\d+)", designation or "", re.IGNORECASE)
    return m.group(1) if m else ""


def fetch_by_designations(designations: list[str]) -> dict[str, dict]:
    """Exact match first; first-number-group match as fallback. Keyed by queried string."""
    out: dict[str, dict] = {}
    if not designations:
        return out
    rows = query(f"SELECT {_COLS} FROM standards WHERE designation = ANY(%s)", (designations,))
    for r in rows:
        out.setdefault(r["designation"], r)
    missing = [d for d in designations if d not in out and d]
    if missing:
        cores = sorted({_core(d) for d in missing} - {""})
        if cores:
            extra = query(
                f"SELECT {_COLS} FROM standards "
                "WHERE (regexp_match(designation, 'IS\\s*(\\d+)', 'i'))[1] = ANY(%s)",
                (cores,),
            )
            by_core: dict[str, dict] = {}
            for r in extra:
                core = _core(r["designation"])
                prev = by_core.get(core)
                if prev is None or (r.get("year") or "") > (prev.get("year") or ""):
                    by_core[core] = r
            for d in missing:
                row = by_core.get(_core(d))
                if row:
                    out[d] = row
    return out


def qco_snapshot() -> dict[str, dict]:
    """QCO entries keyed by designation, loaded once from YAML."""
    global _qco
    with _qco_lock:
        if _qco is None:
            raw = yaml.safe_load(find_data("qco_snapshot.yaml").read_text(encoding="utf-8"))
            _qco = {e["designation"]: e for e in raw.get("entries", []) if e.get("designation")}
        return _qco


def valid_cores() -> set[str]:
    """First IS number group of every known designation (guardrail allow-list)."""
    global _valid_cores
    with _qco_lock:
        if _valid_cores is None:
            rows = query("SELECT DISTINCT designation FROM standards")
            cores = set()
            for r in rows:
                m = re.search(r"IS\s*(\d+)", r["designation"] or "", re.IGNORECASE)
                if m:
                    cores.add(m.group(1))
            _valid_cores = cores
        return _valid_cores
