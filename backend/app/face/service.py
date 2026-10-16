"""Face service: enroll + recognize. Enrolled-only — recognize returns a match ONLY against people the
user enrolled; an unknown face returns recognized=False. Never identifies strangers.
"""
from __future__ import annotations

import logging
import os

from .embedder import Embedder, build_embedder
from .store import FaceStore

log = logging.getLogger("aiglass.face")


class FaceService:
    def __init__(self, embedder: Embedder | None = None, store: FaceStore | None = None) -> None:
        self._embedder = embedder or build_embedder()
        self._store = store or FaceStore()
        self._threshold = float(os.getenv("FACE_THRESHOLD", "0.5"))

    def enroll(self, image_bytes: bytes, name: str, notes: str = "", lookup_query: str = "") -> dict:
        if not name.strip():
            return {"ok": False, "error": "name required"}
        emb = self._embedder.embed(image_bytes)
        if emb is None:
            return {"ok": False, "error": "no face detected in image"}
        fid = self._store.enroll(name.strip(), emb, notes, lookup_query)
        log.info("enrolled name=%r id=%d", name, fid)
        return {"ok": True, "id": fid, "name": name.strip()}

    def recognize(self, image_bytes: bytes) -> dict:
        emb = self._embedder.embed(image_bytes)
        if emb is None:
            return {"recognized": False, "reason": "no face detected"}
        match = self._store.match(emb, self._threshold)
        if not match:
            return {"recognized": False, "reason": "no match among enrolled people"}
        log.info("recognized name=%r score=%s", match["name"], match["score"])
        return {"recognized": True, **match}

    def list(self) -> list[str]:
        return sorted({f["name"] for f in self._store.all()})

    def delete(self, name: str) -> int:
        return self._store.delete(name)
