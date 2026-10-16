"""SQLite-backed memory + transcript store. Stdlib only.

Search here is plain keyword LIKE — good enough for v1 and for tests. For production, swap this class
for a Postgres + pgvector implementation with the same method signatures (embed on write, cosine search
on read); nothing else in the backend needs to change.
"""
from __future__ import annotations

import sqlite3
import threading
import time
from dataclasses import dataclass


@dataclass
class Transcript:
    id: int
    ts: float
    text: str
    speaker: str | None


@dataclass
class Memory:
    id: int
    ts: float
    kind: str          # e.g. "action_item", "fact", "summary"
    text: str
    source: str | None


class MemoryStore:
    def __init__(self, path: str = ":memory:") -> None:
        # check_same_thread=False: FastAPI serves sync endpoints on a threadpool but async ones on the
        # event-loop thread, so one connection is touched from several threads. A lock serializes access.
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            self._db.executescript(
                """
                CREATE TABLE IF NOT EXISTS transcripts (
                    id      INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts      REAL NOT NULL,
                    text    TEXT NOT NULL,
                    speaker TEXT
                );
                CREATE TABLE IF NOT EXISTS memories (
                    id     INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts     REAL NOT NULL,
                    kind   TEXT NOT NULL,
                    text   TEXT NOT NULL,
                    source TEXT
                );
                """
            )
            self._db.commit()

    # --- writes ---------------------------------------------------------
    def add_transcript(self, text: str, speaker: str | None = None, ts: float | None = None) -> int:
        ts = time.time() if ts is None else ts
        with self._lock:
            cur = self._db.execute(
                "INSERT INTO transcripts (ts, text, speaker) VALUES (?, ?, ?)", (ts, text, speaker)
            )
            self._db.commit()
            return int(cur.lastrowid)

    def add_memory(self, kind: str, text: str, source: str | None = None, ts: float | None = None) -> int:
        ts = time.time() if ts is None else ts
        with self._lock:
            cur = self._db.execute(
                "INSERT INTO memories (ts, kind, text, source) VALUES (?, ?, ?, ?)", (ts, kind, text, source)
            )
            self._db.commit()
            return int(cur.lastrowid)

    # --- reads ----------------------------------------------------------
    def search_memories(self, query: str, limit: int = 10) -> list[Memory]:
        with self._lock:
            rows = self._db.execute(
                "SELECT * FROM memories WHERE text LIKE ? ORDER BY ts DESC LIMIT ?",
                (f"%{query}%", limit),
            ).fetchall()
        return [Memory(r["id"], r["ts"], r["kind"], r["text"], r["source"]) for r in rows]

    def memories(self, kind: str | None = None, limit: int = 100) -> list[Memory]:
        with self._lock:
            if kind is None:
                rows = self._db.execute(
                    "SELECT * FROM memories ORDER BY ts DESC LIMIT ?", (limit,)
                ).fetchall()
            else:
                rows = self._db.execute(
                    "SELECT * FROM memories WHERE kind = ? ORDER BY ts DESC LIMIT ?", (kind, limit)
                ).fetchall()
        return [Memory(r["id"], r["ts"], r["kind"], r["text"], r["source"]) for r in rows]

    def recent_transcripts(self, limit: int = 50) -> list[Transcript]:
        with self._lock:
            rows = self._db.execute(
                "SELECT * FROM transcripts ORDER BY ts DESC LIMIT ?", (limit,)
            ).fetchall()
        return [Transcript(r["id"], r["ts"], r["text"], r["speaker"]) for r in rows]

    def close(self) -> None:
        self._db.close()
