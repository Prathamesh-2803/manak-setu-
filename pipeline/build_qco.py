"""Build data/qco_snapshot.yaml from crawled details.

Source of truth: detail-page fields where Certification == 'Mandatory Certification',
QCO status/date scraped from the 'Member Secretary' free-text blob:
  '... QCO Notified & Implemented Implemented On::15-02-2021 Summary/...'
Also captures other statuses seen in the wild (notified-not-implemented, proposed).

Usage:
  python pipeline/build_qco.py
"""

from __future__ import annotations

import json
import pathlib
import re
from datetime import date

RAW = pathlib.Path("data/raw")
OUT = pathlib.Path("data/qco_snapshot.yaml")

STATUS_PATTERNS = [
    (re.compile(r"QCO Notified & Implemented\s+Implemented On::(\d{2}-\d{2}-\d{4})"), "notified_implemented"),
    (re.compile(r"QCO Notified & Implemented"), "notified_implemented"),
    (re.compile(r"QCO Notified"), "notified"),
    (re.compile(r"QCO Proposed"), "proposed"),
    (re.compile(r"Under consideration", re.I), "under_consideration"),
]
DATE_RE = re.compile(r"(\d{2})-(\d{2})-(\d{4})")


def iso(dd: str, mm: str, yyyy: str) -> str:
    return f"{yyyy}-{mm}-{dd}"


def main() -> None:
    entries = []
    no_status = 0
    for f in sorted((RAW / "details").glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        fl = d.get("fields", {})
        if fl.get("Certification") != "Mandatory Certification":
            continue
        blob = fl.get("Member Secretary") or ""
        status = None
        implemented_on = None
        for pat, name in STATUS_PATTERNS:
            m = pat.search(blob)
            if m:
                status = name
                if m.groups():
                    implemented_on = iso(*m.groups()) if len(m.groups()) == 3 else None
                break
        if status is None:
            m = DATE_RE.search(blob)
            if m:
                status = "unknown_dated"
                implemented_on = iso(*m.groups())
            else:
                status = "unknown"
                no_status += 1

        row = d.get("list_row", {})
        entries.append(
            {
                "is": row.get("is_number_raw") or fl.get("IS Number"),
                "designation": row.get("designation"),
                "title": (fl.get("IS Title") or row.get("title") or "").strip(),
                "aspect": fl.get("Aspect"),
                "committee": fl.get("Technical Committee"),
                "ministry": fl.get("Relevant Ministries"),
                "qco_status": status,
                "implemented_on": implemented_on,
            }
        )

    entries.sort(key=lambda e: (e["qco_status"], e["implemented_on"] or "", e["is"] or ""))
    counts: dict[str, int] = {}
    for e in entries:
        counts[e["qco_status"]] = counts.get(e["qco_status"], 0) + 1

    lines = [
        "# Manak Setu — QCO (Quality Control Order) snapshot",
        "# AUTO-GENERATED from data/raw/details (Mandatory Certification records).",
        "# Regenerate: python pipeline/build_qco.py",
        f"# Generated: {date.today().isoformat()} | Total mandatory-cert standards: {len(entries)}",
        f"# Status counts: {json.dumps(counts, sort_keys=True)}",
        "version: 1",
        f"generated: {date.today().isoformat()}",
        f"total: {len(entries)}",
        f"status_counts: {json.dumps(counts, sort_keys=True)}",
        "entries:",
    ]
    for e in entries:
        is_txt = json.dumps(e["is"])
        title = json.dumps(e["title"])
        lines.append(f"  - is: {is_txt}")
        lines.append(f"    designation: {json.dumps(e['designation'])}")
        lines.append(f"    title: {title}")
        lines.append(f"    qco_status: {e['qco_status']}")
        lines.append(f"    implemented_on: {e['implemented_on']}")
        lines.append(f"    ministry: {json.dumps(e['ministry'])}")
        lines.append(f"    committee: {json.dumps(e['committee'])}")

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT} — {len(entries)} entries; status counts: {counts}; no_status={no_status}")


if __name__ == "__main__":
    main()
