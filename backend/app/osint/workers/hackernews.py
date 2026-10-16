"""Hacker News worker — Algolia HN Search API (no key)."""
from __future__ import annotations

import httpx

from ..result import WorkerResult
from .base import worker

HN = "https://hn.algolia.com/api/v1/search"


@worker("hackernews", timeout=10)
async def hackernews_worker(query: str) -> WorkerResult:
    async with httpx.AsyncClient(timeout=8) as client:
        r = await client.get(HN, params={"query": query, "tags": "story", "hitsPerPage": 5})
        r.raise_for_status()
        hits = r.json().get("hits", [])
    return WorkerResult(
        provider="hackernews",
        success=True,
        confidence=0.5 if hits else 0.0,
        data={"stories": [
            {"title": h.get("title"), "url": h.get("url"),
             "points": h.get("points"), "author": h.get("author")}
            for h in hits
        ]},
    )
