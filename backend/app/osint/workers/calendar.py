"""Calendar worker — graceful. Real calendar access needs Google/CalDAV OAuth; until wired, reports
not-configured. Implement the fetch in the body."""
from __future__ import annotations

from ..result import WorkerResult
from .base import worker


@worker("calendar", timeout=5, cache=False)
async def calendar_worker(query: str) -> WorkerResult:
    return WorkerResult.failed("calendar", "calendar source not configured (needs Google/CalDAV OAuth)")
