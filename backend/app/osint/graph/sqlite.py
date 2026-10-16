"""SQLite-backed knowledge-graph store. Implements the `GraphStore` interface (see ../graph.py) so it can
be swapped for Neo4j/Qdrant/LanceDB without touching the engine. Stdlib only; thread-safe."""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from typing import Any

from ..settings import load_settings


class SqliteGraphStore:
    def __init__(self, path: str | None = None) -> None:
        self._path = path or load_settings().db_path
        self._db = sqlite3.connect(self._path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._init()

    def _init(self) -> None:
        with self._lock:
            self._db.executescript(
                """
                CREATE TABLE IF NOT EXISTS kg_entities (
                    id         TEXT PRIMARY KEY,
                    type       TEXT,
                    name       TEXT,
                    attributes TEXT,
                    updated    REAL
                );
                CREATE TABLE IF NOT EXISTS kg_edges (
                    subject    TEXT,
                    predicate  TEXT,
                    object     TEXT,
                    confidence REAL,
                    provider   TEXT,
                    UNIQUE(subject, predicate, object)
                );
                CREATE INDEX IF NOT EXISTS kg_entities_name ON kg_entities(name);
                """
            )
            self._db.commit()

    def upsert_entity(self, entity_id: str, etype: str, name: str, attributes: dict) -> None:
        with self._lock:
            self._db.execute(
                "INSERT INTO kg_entities (id, type, name, attributes, updated) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET type=excluded.type, name=excluded.name, "
                "attributes=excluded.attributes, updated=excluded.updated",
                (entity_id, etype, name, json.dumps(attributes or {}), time.time()),
            )
            self._db.commit()

    def add_relationship(self, subject: str, predicate: str, obj: str,
                         confidence: float = 0.5, provider: str | None = None) -> None:
        with self._lock:
            self._db.execute(
                "INSERT OR IGNORE INTO kg_edges (subject, predicate, object, confidence, provider) "
                "VALUES (?, ?, ?, ?, ?)",
                (subject, predicate, obj, confidence, provider),
            )
            self._db.commit()

    def get_entity(self, entity_id: str) -> dict | None:
        with self._lock:
            row = self._db.execute("SELECT * FROM kg_entities WHERE id = ?", (entity_id,)).fetchone()
        return self._row(row) if row else None

    def relationships(self, entity_id: str) -> list[dict]:
        with self._lock:
            rows = self._db.execute(
                "SELECT * FROM kg_edges WHERE subject = ? OR object = ?", (entity_id, entity_id)
            ).fetchall()
        return [dict(r) for r in rows]

    def neighbors(self, entity_id: str) -> list[dict]:
        seen: set[str] = set()
        for r in self.relationships(entity_id):
            seen.add(r["object"] if r["subject"] == entity_id else r["subject"])
        out: list[dict] = []
        for nid in seen:
            e = self.get_entity(nid)
            if e:
                out.append(e)
        return out

    def search(self, query: str, limit: int = 10) -> list[dict]:
        with self._lock:
            rows = self._db.execute(
                "SELECT * FROM kg_entities WHERE name LIKE ? ORDER BY updated DESC LIMIT ?",
                (f"%{query}%", limit),
            ).fetchall()
        return [self._row(r) for r in rows]

    @staticmethod
    def _row(row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        d["attributes"] = json.loads(d.get("attributes") or "{}")
        return d
