"""Knowledge graph.

The engine talks only to `KnowledgeGraph`; concrete stores (SQLite now, Neo4j/Qdrant/LanceDB later) live
behind the `GraphStore` interface. (Facade lives in the package `__init__` rather than a sibling `graph.py`
because a module and package of the same name can't coexist in one directory.)
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..entity import Person, Relationship


@runtime_checkable
class GraphStore(Protocol):
    def upsert_entity(self, entity_id: str, etype: str, name: str, attributes: dict) -> None: ...
    def add_relationship(self, subject: str, predicate: str, obj: str,
                         confidence: float = 0.5, provider: str | None = None) -> None: ...
    def get_entity(self, entity_id: str) -> dict | None: ...
    def neighbors(self, entity_id: str) -> list[dict]: ...
    def relationships(self, entity_id: str) -> list[dict]: ...
    def search(self, query: str, limit: int = 10) -> list[dict]: ...


def _default_store() -> GraphStore:
    from .sqlite import SqliteGraphStore
    return SqliteGraphStore()


class KnowledgeGraph:
    """Stores resolved entities + relationships. `update()` is the write path the engine calls; the read
    helpers (lookup/neighbors/relationships/search) back the MCP/graph queries."""

    def __init__(self, store: GraphStore | None = None) -> None:
        self._store = store or _default_store()

    def update(self, person: Person, relationships: list[Relationship] | None = None) -> None:
        if person.is_empty():
            return
        self._store.upsert_entity(
            person.id, person.type.value, person.name or person.github,
            {
                "company": person.company,
                "location": person.location,
                "website": person.website,
                "github": person.github,
                **(person.attributes or {}),
            },
        )
        # derive canonical relationships from the resolved person
        if person.company:
            cid = f"company:{person.company.strip().lower()}"
            self._store.upsert_entity(cid, "company", person.company, {})
            self._store.add_relationship(person.id, "works_at", cid, person.confidence or 0.5, "resolver")
        for repo in (person.attributes.get("repos") or [])[:5]:
            name = str(repo.get("name") or "").strip()
            if not name:
                continue
            rid = f"repository:{name.lower()}"
            self._store.upsert_entity(rid, "repository", name, {"language": repo.get("language")})
            self._store.add_relationship(person.id, "created", rid, 0.6, "github")
        for rel in (relationships or []):
            self._store.add_relationship(rel.subject, rel.predicate, rel.obj, rel.confidence, rel.provider)

    def lookup(self, entity_id: str) -> dict | None:
        return self._store.get_entity(entity_id)

    def neighbors(self, entity_id: str) -> list[dict]:
        return self._store.neighbors(entity_id)

    def relationships(self, entity_id: str) -> list[dict]:
        return self._store.relationships(entity_id)

    def search(self, query: str, limit: int = 10) -> list[dict]:
        return self._store.search(query, limit)


__all__ = ["GraphStore", "KnowledgeGraph"]
