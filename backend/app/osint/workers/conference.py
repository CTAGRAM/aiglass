"""Conference worker — graceful placeholder.

Real conference data (speaker/talk listings) needs a specific source or API. Until one is
configured this returns an empty *successful* result rather than fabricating data — so the pipeline treats
it as "nothing found here", not a failure. Wire a real source (e.g. a conf API / scraper) inside the body.
"""
from __future__ import annotations

from ..result import WorkerResult
from .base import worker


@worker("conference", timeout=5, cache=False)
async def conference_worker(query: str) -> WorkerResult:
    return WorkerResult(
        provider="conference",
        success=True,
        confidence=0.0,
        data={"note": "conference source not configured"},
    )
