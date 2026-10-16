"""Memory worker — searches the user's captured aiGlass memory (SQLite). Local + fast (<30ms target)."""
from __future__ import annotations

import asyncio

from ...config import load_settings
from ...memory.store import MemoryStore
from ..result import WorkerResult
from .base import worker


@worker("memory", timeout=3, retries=1)
async def memory_worker(query: str) -> WorkerResult:
    store = MemoryStore(load_settings().db_path)
    memories = await asyncio.to_thread(store.search_memories, query, 10)
    return WorkerResult(
        provider="memory",
        success=True,
        confidence=1.0 if memories else 0.0,
        data={"memories": [m.__dict__ for m in memories]},
    )
