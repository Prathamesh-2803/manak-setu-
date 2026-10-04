"""Load crawled standards into Neo4j: nodes + REFERS_TO + SUPERSEDED_BY edges.

Sources: data/raw/standards_list.jsonl + data/raw/details/<id>.json

Usage:
  python pipeline/load_graph.py
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

from neo4j import GraphDatabase

RAW = Path("data/raw")
URI = os.environ.get("NEO4J_URL", "bolt://localhost:7687")
USER = os.environ.get("NEO4J_USER", "neo4j")
PASSWORD = os.environ.get("NEO4J_PASSWORD", "manak_setu")

NONE_VALUES = {"", "none", "none.", "n/a", "na", "not applicable"}


def norm_key(text: str) -> str:
    """Aggressive normalization so 'IS 10052 (Part 1/Sec 6):2022' == 'IS 10052 : Part 1 : Sec 6 : 2022'."""
    return re.sub(r"[^A-Z0-9]", "", (text or "").upper())


def load_data() -> tuple[list[dict], list[dict], dict[str, str]]:
    rows = [json.loads(x) for x in (RAW / "standards_list.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    details = {f.stem: json.loads(f.read_text(encoding="utf-8")) for f in (RAW / "details").glob("*.json")}

    # supersession lookup: normalized is_number_raw / designation+year -> id
    key_to_id: dict[str, str] = {}
    for r in rows:
        rid = r.get("id")
        if not rid:
            continue
        for candidate in (r.get("is_number_raw"), f"{r.get('designation', '')}:{r.get('year', '')}"):
            k = norm_key(candidate)
            if k and k not in key_to_id:
                key_to_id[k] = rid

    nodes: list[dict] = []
    for r in rows:
        rid = r.get("id")
        if not rid:
            continue
        fl = details.get(rid, {}).get("fields", {})
        nodes.append(
            {
                "id": rid,
                "designation": r.get("designation") or r.get("is_number_raw"),
                "is_number_raw": r.get("is_number_raw"),
                "year": r.get("year"),
                "title": r.get("title") or "",
                "short_title": fl.get("Short Commom Man's Title") or fl.get("Short Common Man's Title"),
                "aspect": fl.get("Aspect"),
                "certification": fl.get("Certification"),
                "iso_equivalent": r.get("iso_equivalent"),
                "committee": fl.get("Technical Committee"),
                "dept": fl.get("Technical Department"),
                "group": r.get("group_name"),
                "superseding_is": fl.get("Superseding IS"),
                "degree_equivalence": fl.get("Degree of Equivalence"),
                "status": "current",
            }
        )

    edges: dict[tuple[str, str], None] = {}
    sup_edges: list[tuple[str, str]] = []
    placeholders: dict[str, dict] = {}
    sup_unmatched = 0

    def add_supersession(old_designation: str, new_id: str) -> None:
        """BIS field 'Superseding IS: X' on record Y means Y supersedes X (X is old).
        Edge: (X)-[:SUPERSEDED_BY]->(Y). X is usually withdrawn and not in the
        classification lists, so create a placeholder node for it."""
        part = old_designation.strip().strip(",;")
        if not part or part.lower() in NONE_VALUES:
            return
        k = norm_key(part)
        if not k:
            return
        existing = key_to_id.get(k)
        if existing and existing != new_id:
            sup_edges.append((existing, new_id))
            return
        pid = f"sup:{k}"
        if pid != new_id:
            placeholders.setdefault(
                pid,
                {"id": pid, "designation": part, "status": "superseded_old", "title": "(withdrawn standard not in classification lists)"},
            )
            sup_edges.append((pid, new_id))
        else:
            sup_unmatched += 1

    for rid, d in details.items():
        for e in d.get("cross_refs_out", []) + d.get("cross_refs_in", []):
            other = e.get("id")
            if other and other != rid:
                edges[(rid, other)] = None
        sup = (d.get("fields", {}).get("Superseding IS") or "").strip()
        if sup and sup.lower() not in NONE_VALUES:
            for part in re.split(r"\s*(?:,|\band\b)\s*", sup):
                if norm_key(part):
                    add_supersession(part, rid)

    # dedupe supersession
    sup_edges = list(dict.fromkeys(sup_edges))
    nodes.extend(placeholders.values())
    print(
        f"[load] nodes={len(nodes)} (incl {len(placeholders)} supersession placeholders) "
        f"refers_to={len(edges)} superseded_by={len(sup_edges)} sup_unmatched={sup_unmatched}"
    )
    return nodes, [{"src": a, "dst": b} for a, b in edges], sup_edges


def main() -> None:
    nodes, ref_rows, sup_edges = load_data()
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

    def run(tx, query, **kw):
        return tx.run(query, **kw).consume()

    with driver.session() as s:
        s.run("MATCH (n) DETACH DELETE n")
        s.run("CREATE CONSTRAINT std_id IF NOT EXISTS FOR (s:Standard) REQUIRE s.id IS UNIQUE")

        # nodes in chunks
        for i in range(0, len(nodes), 1000):
            chunk = nodes[i : i + 1000]
            s.run(
                """
                UNWIND $rows AS row
                MERGE (s:Standard {id: row.id})
                SET s += row
                """,
                rows=chunk,
            )
        print(f"[neo4j] nodes created: {len(nodes)}")

        # REFERS_TO edges (both nodes must exist)
        for i in range(0, len(ref_rows), 2000):
            chunk = ref_rows[i : i + 2000]
            s.run(
                """
                UNWIND $rows AS e
                MATCH (a:Standard {id: e.src}), (b:Standard {id: e.dst})
                MERGE (a)-[:REFERS_TO]->(b)
                """,
                rows=chunk,
            )
        print(f"[neo4j] refers_to attempted: {len(ref_rows)}")

        for i in range(0, len(sup_edges), 2000):
            chunk = [{"src": a, "dst": b} for a, b in sup_edges[i : i + 2000]]
            s.run(
                """
                UNWIND $rows AS e
                MATCH (a:Standard {id: e.src}), (b:Standard {id: e.dst})
                MERGE (a)-[:SUPERSEDED_BY]->(b)
                """,
                rows=chunk,
            )
        print(f"[neo4j] superseded_by: {len(sup_edges)}")

        # verify
        n = s.run("MATCH (s:Standard) RETURN count(s) AS c").single()["c"]
        e = s.run("MATCH ()-[r:REFERS_TO]->() RETURN count(r) AS c").single()["c"]
        sv = s.run("MATCH ()-[r:SUPERSEDED_BY]->() RETURN count(r) AS c").single()["c"]
        top = s.run(
            """
            MATCH (s:Standard)-[r:REFERS_TO]->()
            RETURN s.designation AS d, count(r) AS c ORDER BY c DESC LIMIT 5
            """
        ).data()
        print(f"[verify] nodes={n} refers_to={e} superseded_by={sv}")
        print("[verify] most-referenced:", [(t["d"], t["c"]) for t in top])

    driver.close()


if __name__ == "__main__":
    t0 = time.time()
    main()
    print(f"done in {time.time() - t0:.1f}s")
