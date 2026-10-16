"""Podcast worker — Apple/iTunes podcast search (no key)."""
from __future__ import annotations

import httpx

from ..result import WorkerResult
from .base import worker

ITUNES = "https://itunes.apple.com/search"


@worker("podcast", timeout=10)
async def podcast_worker(query: str) -> WorkerResult:
    async with httpx.AsyncClient(timeout=8) as client:
        r = await client.get(ITUNES, params={"term": query, "media": "podcast", "limit": 5})
        r.raise_for_status()
        results = r.json().get("results", [])
    return WorkerResult(
        provider="podcast",
        success=True,
        confidence=0.4 if results else 0.0,
        data={"podcasts": [
            {"name": p.get("collectionName"), "artist": p.get("artistName"),
             "url": p.get("collectionViewUrl"), "genre": p.get("primaryGenreName")}
            for p in results
        ]},
    )
