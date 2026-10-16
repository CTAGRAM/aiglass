"""Email worker — graceful. Real inbox access needs Gmail/IMAP OAuth; until wired, reports not-configured
so the pipeline treats it as 'no source' rather than fabricating. Implement the fetch in the body."""
from __future__ import annotations

from ..result import WorkerResult
from .base import worker


@worker("email", timeout=5, cache=False)
async def email_worker(query: str) -> WorkerResult:
    return WorkerResult.failed("email", "email source not configured (needs Gmail/IMAP OAuth)")
