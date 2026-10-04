"""Graph sanity checks: Version Guard chain, placeholders, allied walk."""

from neo4j import GraphDatabase

d = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "manak_setu"))

with d.session() as s:
    print("--- IS 9637 anywhere? ---")
    rows = s.run(
        "MATCH (n) WHERE n.is_number_raw CONTAINS '9637' OR n.designation CONTAINS '9637' "
        "RETURN n.id AS id, n.designation AS d, n.status AS st, left(coalesce(n.title,''), 50) AS t LIMIT 8"
    ).data()
    print(rows or "NOT FOUND")

    print("--- placeholder supersession examples ---")
    rows = s.run(
        "MATCH (o)-[:SUPERSEDED_BY]->(n) WHERE o.status = 'superseded_old' "
        "RETURN o.designation AS old, n.designation AS new LIMIT 6"
    ).data()
    for r in rows:
        print(" ", r)

    print("--- supersession where old IS exists in dataset ---")
    rows = s.run(
        "MATCH (o)-[:SUPERSEDED_BY]->(n) WHERE o.status = 'current' "
        "RETURN o.designation AS old, n.designation AS new LIMIT 6"
    ).data()
    for r in rows:
        print(" ", r)

    print("--- allied walk: from a product spec, neighbors + aspects ---")
    rows = s.run(
        "MATCH (s:Standard)-[:REFERS_TO]->(t) WHERE s.designation = 'IS 1786' "
        "RETURN t.designation AS d, t.aspect AS aspect, left(coalesce(t.title,''), 45) AS title LIMIT 8"
    ).data()
    print(rows or "IS 1786 has no out-edges")

    print("--- what is IS 1786? ---")
    rows = s.run(
        "MATCH (n) WHERE n.designation STARTS WITH 'IS 1786' "
        "RETURN n.designation AS d, n.aspect AS aspect, left(coalesce(n.title,''), 60) AS t LIMIT 5"
    ).data()
    for r in rows:
        print(" ", r)

    print("--- graph stats ---")
    print(s.run("MATCH (n) RETURN count(n) AS nodes").single())
    print(s.run("MATCH ()-[r:REFERS_TO]->() RETURN count(r) AS refs").single())
    print(s.run("MATCH ()-[r:SUPERSEDED_BY]->() RETURN count(r) AS sup").single())

d.close()
