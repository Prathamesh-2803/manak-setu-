"""Load crawled BIS data into Postgres (idempotent — drop + recreate).

Sources:
  data/raw/standards_list.jsonl   (list rows: designation, title, group, iso)
  data/raw/details/<id>.json      (aspect, committee, supersession, cross-refs, classification)

Usage:
  python pipeline/load_postgres.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import psycopg

RAW = Path("data/raw")
DSN = os.environ.get("DATABASE_URL", "postgresql://manak:manak@localhost:5432/manak_setu")

SCHEMA = """
DROP TABLE IF EXISTS cross_refs CASCADE;
DROP TABLE IF EXISTS standards CASCADE;

CREATE TABLE standards (
    id                TEXT PRIMARY KEY,
    designation       TEXT,               -- IS 1786 : 2018
    is_number_raw     TEXT,
    year              TEXT,
    title             TEXT NOT NULL DEFAULT '',
    short_title       TEXT,
    iso_equivalent    TEXT,               -- from list + Identical/Equivalent field
    revision_count    INT,
    amendment         TEXT,
    aspect            TEXT,               -- Product Specification / Methods of tests / ...
    language          TEXT,
    tech_department   TEXT,
    tech_committee    TEXT,
    member_secretary  TEXT,
    superseding_is    TEXT,
    degree_equivalence TEXT,
    certification     TEXT,               -- Mandatory Certification / None
    cls_group         TEXT,
    cls_sub_group     TEXT,
    cls_sub_sub_group TEXT,
    ministries        TEXT,
    itc_hs_code       TEXT,
    group_list_id     INT,
    group_name        TEXT,
    detail_url        TEXT,
    fields            JSONB              -- full detail fields dict
);

CREATE INDEX ON standards USING GIN (to_tsvector('english', title));
CREATE INDEX ON standards (aspect);
CREATE INDEX ON standards (certification);
CREATE INDEX ON standards (superseding_is);

CREATE TABLE cross_refs (
    src_id      TEXT NOT NULL,
    dst_id      TEXT NOT NULL,
    direction   TEXT NOT NULL,            -- 'out' (src refers to dst) | 'in' (dst refers to src)
    designation TEXT,
    PRIMARY KEY (src_id, dst_id, direction)
);
CREATE INDEX ON cross_refs (dst_id);
"""


def load_rows() -> list[dict]:
    rows = []
    for line in (RAW / "standards_list.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def detail_map() -> dict[str, dict]:
    out = {}
    for f in (RAW / "details").glob("*.json"):
        out[f.stem] = json.loads(f.read_text(encoding="utf-8"))
    return out


def main() -> None:
    rows = load_rows()
    details = detail_map()
    print(f"[load] list rows={len(rows)} details={len(details)}")

    refs: set[tuple[str, str, str, str]] = set()
    for did, d in details.items():
        for e in d.get("cross_refs_out", []):
            refs.add((did, e.get("id") or "", "out", e.get("designation") or ""))
        for e in d.get("cross_refs_in", []):
            refs.add((e.get("id") or "", did, "in", e.get("designation") or ""))
    refs = {r for r in refs if r[0] and r[1] and r[0] != r[1]}

    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute(SCHEMA)
        cols = (
            "id, designation, is_number_raw, year, title, short_title, iso_equivalent, "
            "revision_count, amendment, aspect, language, tech_department, tech_committee, "
            "member_secretary, superseding_is, degree_equivalence, certification, "
            "cls_group, cls_sub_group, cls_sub_sub_group, ministries, itc_hs_code, "
            "group_list_id, group_name, detail_url, fields"
        )
        placeholder = "(" + ",".join(["%s"] * 26) + ")"
        batch = []
        for r in rows:
            rid = r.get("id")
            if not rid:
                continue
            d = details.get(rid, {})
            fl = d.get("fields", {})
            iso = ", ".join(
                p for p in [r.get("iso_equivalent", ""), fl.get("Identical/Equivalent International Standard(s)", "")] if p
            )
            batch.append(
                (
                    rid,
                    r.get("designation"),
                    r.get("is_number_raw"),
                    r.get("year"),
                    r.get("title") or fl.get("IS Title", ""),
                    fl.get("Short Commom Man's Title") or fl.get("Short Common Man's Title"),
                    iso or None,
                    r.get("revision_count"),
                    r.get("amendment"),
                    fl.get("Aspect"),
                    fl.get("Language"),
                    fl.get("Technical Department"),
                    fl.get("Technical Committee"),
                    fl.get("Member Secretary"),
                    fl.get("Superseding IS"),
                    fl.get("Degree of Equivalence"),
                    fl.get("Certification"),
                    fl.get("Group"),
                    fl.get("Sub Group"),
                    fl.get("Sub Sub Group"),
                    fl.get("Relevant Ministries"),
                    fl.get("ITC-HS Code"),
                    r.get("group_list_id"),
                    r.get("group_name"),
                    r.get("detail_url"),
                    json.dumps(fl, ensure_ascii=False),
                )
            )
        cur.executemany(f"INSERT INTO standards ({cols}) VALUES {placeholder} ON CONFLICT (id) DO UPDATE SET {', '.join(f'{c}=EXCLUDED.{c}' for c in cols.split(', '))}", batch)
        print(f"[load] standards inserted: {len(batch)}")

        cur.executemany(
            "INSERT INTO cross_refs (src_id, dst_id, direction, designation) VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            sorted(refs),
        )
        print(f"[load] cross_refs inserted: {len(refs)}")

        cur.execute("SELECT COUNT(*) FROM standards")
        print("[verify] standards =", cur.fetchone()[0])
        cur.execute("SELECT COUNT(*) FROM cross_refs")
        print("[verify] cross_refs =", cur.fetchone()[0])
        cur.execute("SELECT aspect, COUNT(*) FROM standards GROUP BY aspect ORDER BY COUNT(*) DESC LIMIT 6")
        for a, c in cur.fetchall():
            print(f"  aspect {a}: {c}")


if __name__ == "__main__":
    main()
