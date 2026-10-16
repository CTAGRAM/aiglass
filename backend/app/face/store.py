"""SQLite store for enrolled faces. Cosine match is pure Python (embeddings are unit vectors → dot product).
Only enrolled people are ever stored/compared — there is no public database here by design.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time

from ..config import load_settings


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


class FaceStore:
    def __init__(self, path: str | None = None) -> None:
        self._db = sqlite3.connect(path or load_settings().db_path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._init()

    def _init(self) -> None:
        with self._lock:
            self._db.execute(
                """CREATE TABLE IF NOT EXISTS faces (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    name         TEXT NOT NULL,
                    notes        TEXT,
                    lookup_query TEXT,
                    embedding    TEXT NOT NULL,
                    ts           REAL
                )"""
            )
            self._db.commit()

    def enroll(self, name: str, embedding: list[float], notes: str = "", lookup_query: str = "") -> int:
        with self._lock:
            cur = self._db.execute(
                "INSERT INTO faces (name, notes, lookup_query, embedding, ts) VALUES (?, ?, ?, ?, ?)",
                (name, notes, lookup_query, json.dumps(embedding), time.time()),
            )
            self._db.commit()
            return int(cur.lastrowid)

    def all(self) -> list[dict]:
        with self._lock:
            rows = self._db.execute("SELECT id, name, notes, lookup_query, ts FROM faces").fetchall()
        return [dict(r) for r in rows]

    def find(self, name: str) -> dict | None:
        """The saved record for one enrolled person (case-insensitive), or None if they aren't saved.
        A person enrolled from several photos has several rows; the newest non-empty fields win."""
        with self._lock:
            rows = self._db.execute(
                "SELECT name, notes, lookup_query, ts FROM faces WHERE lower(name) = lower(?) ORDER BY ts DESC",
                (name.strip(),),
            ).fetchall()
        if not rows:
            return None
        record = dict(rows[0])
        record["notes"] = next((r["notes"] for r in rows if r["notes"]), "")
        record["lookup_query"] = next((r["lookup_query"] for r in rows if r["lookup_query"]), "")
        return record

    def match(self, embedding: list[float], threshold: float) -> dict | None:
        """Best enrolled match at or above threshold, else None (never guesses on an unknown face)."""
        best: sqlite3.Row | None = None
        best_score = -1.0
        with self._lock:
            rows = self._db.execute(
                "SELECT name, notes, lookup_query, embedding FROM faces"
            ).fetchall()
        for r in rows:
            emb = json.loads(r["embedding"])
            if len(emb) != len(embedding):          # different embedder dim → skip
                continue
            s = _cosine(embedding, emb)
            if s > best_score:
                best_score, best = s, r
        if best is not None and best_score >= threshold:
            return {"name": best["name"], "notes": best["notes"] or "",
                    "lookup_query": best["lookup_query"] or "", "score": round(best_score, 3)}
        return None

    def delete(self, name: str) -> int:
        with self._lock:
            cur = self._db.execute("DELETE FROM faces WHERE name = ?", (name,))
            self._db.commit()
            return cur.rowcount
