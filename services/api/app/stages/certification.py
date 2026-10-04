"""Certification Oracle: QCO status + scheme for a standard."""

from __future__ import annotations

from app.db import pg as db


def lookup(designation: str, row: dict | None) -> dict:
    qco = db.qco_snapshot().get(designation or "")
    cert = (row or {}).get("certification") or ""
    mandatory = bool(qco) or cert.strip().lower() == "mandatory certification"
    if not mandatory:
        return {"mandatory": False, "scheme": None, "qco_status": None,
                "implemented_on": None, "ministry": None, "source": None}
    status = (qco or {}).get("qco_status")
    return {
        "mandatory": True,
        "scheme": "ISI mark (Standard Mark)",  # default; refined per-scheme in Phase 2
        "qco_status": status,
        "implemented_on": (qco or {}).get("implemented_on"),
        "ministry": (qco or {}).get("ministry"),
        "source": "BIS QCO snapshot 2026-10-04"
        + (f" via {qco['ministry']}" if qco and qco.get("ministry") else ""),
    }
