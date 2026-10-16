"""Knowledge-graph tests (SQLite store + semantic rerank). Zero deps.
    python3 app/osint/tests/test_graph.py       # from backend/
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))  # -> backend/

from app.osint.entity import Person                     # noqa: E402
from app.osint.graph import KnowledgeGraph              # noqa: E402
from app.osint.graph.search import semantic_rerank      # noqa: E402
from app.osint.graph.sqlite import SqliteGraphStore     # noqa: E402


def _kg():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return KnowledgeGraph(SqliteGraphStore(path)), path


def test_graph_update_relationships_and_neighbors():
    kg, path = _kg()
    try:
        p = Person(name="Guillermo Rauch", github="rauchg", company="Vercel", confidence=0.9,
                   attributes={"repos": [{"name": "next.js", "language": "TypeScript"}]})
        kg.update(p)
        e = kg.lookup("person:rauchg")
        assert e and e["name"] == "Guillermo Rauch"
        preds = {r["predicate"] for r in kg.relationships("person:rauchg")}
        assert "works_at" in preds and "created" in preds
        neigh = {n["id"] for n in kg.neighbors("person:rauchg")}
        assert "company:vercel" in neigh and "repository:next.js" in neigh
    finally:
        os.remove(path)


def test_graph_search():
    kg, path = _kg()
    try:
        kg.update(Person(name="Ada Lovelace", github="ada"))
        assert any(h["name"] == "Ada Lovelace" for h in kg.search("Ada"))
    finally:
        os.remove(path)


def test_empty_person_is_noop():
    kg, path = _kg()
    try:
        kg.update(Person())
        assert kg.lookup("person:") is None
    finally:
        os.remove(path)


def test_semantic_rerank():
    ents = [
        {"name": "Next.js", "attributes": {"language": "TypeScript"}},
        {"name": "Django", "attributes": {"language": "Python"}},
    ]
    ranked = semantic_rerank("typescript framework", ents)
    assert ranked[0]["name"] == "Next.js"


def _main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"  FAIL  {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_main())
