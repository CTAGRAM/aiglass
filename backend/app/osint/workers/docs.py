"""Docs worker — graceful. Searches technical documentation once a source (DevDocs / a docs site) is
configured; until then returns an empty successful result (nothing found here). Implement in the body."""
from __future__ import annotations

from ..result import WorkerResult
from .base import worker


@worker("docs", timeout=5, cache=False)
async def docs_worker(query: str) -> WorkerResult:
    return WorkerResult(provider="docs", success=True, confidence=0.0,
                        data={"note": "docs source not configured"})
