"""Local worker — graceful. Placeholder for on-device / local-file knowledge; returns empty success until
a local source is wired (kept distinct from the memory worker). Implement in the body."""
from __future__ import annotations

from ..result import WorkerResult
from .base import worker


@worker("local", timeout=5, cache=False)
async def local_worker(query: str) -> WorkerResult:
    return WorkerResult(provider="local", success=True, confidence=0.0,
                        data={"note": "local source not configured"})
