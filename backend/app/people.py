"""People memory: remember the people the user saves, and recall who they are.

Only people the user saved (with their consent) can be recognised or recalled. For a saved person, recall
returns what the user knows: their notes, recent memories that mention them, and, only when the user saved
a public profile link for them, a summary of that profile from the enrichment engine (`app/osint/`).
Anyone who isn't saved gets `known: False`. There is no path through this module to look up a stranger.
"""
from __future__ import annotations

import asyncio
from typing import Awaitable, Callable

from .face.store import FaceStore
from .memory.store import MemoryStore

Enricher = Callable[[str], Awaitable[dict]]


def default_enricher() -> Enricher | None:
    """The profile-enrichment engine, or None when its optional deps are missing (recall still works)."""
    try:
        from .osint.engine import run
    except Exception:  # noqa: BLE001
        return None
    return run


class PeopleMemory:
    def __init__(self, faces: FaceStore, memory: MemoryStore, enrich: Enricher | None = None) -> None:
        self._faces = faces
        self._memory = memory
        self._enrich = enrich

    def is_saved(self, name: str) -> bool:
        return self._faces.find(name) is not None

    async def recall(self, name: str, recent: int = 5) -> dict:
        person = self._faces.find(name)
        if person is None:
            return {"known": False, "name": name, "message": f"{name} isn't one of your saved people."}

        memories = await asyncio.to_thread(self._memory.search_memories, person["name"], recent)
        out = {
            "known": True,
            "name": person["name"],
            "notes": person["notes"],
            "saved_at": person["ts"],
            "recent": [m.text for m in memories],
            "public_profile": None,
        }
        link = person["lookup_query"].strip()
        if link and self._enrich is not None:
            try:  # best-effort: a slow or failing source never breaks recall
                out["public_profile"] = await self._enrich(link)
            except Exception:  # noqa: BLE001
                pass
        return out
