"""Reddit worker — public search.json (no key). Graceful on Reddit's occasional 403/429."""
from __future__ import annotations

import httpx

from ..result import WorkerResult
from .base import worker


@worker("reddit", timeout=10)
async def reddit_worker(query: str) -> WorkerResult:
    async with httpx.AsyncClient(timeout=8, headers={"User-Agent": "AIGlass/1.0"}) as client:
        r = await client.get(
            "https://www.reddit.com/search.json",
            params={"q": query, "limit": 5, "sort": "relevance"},
        )
        if r.status_code != 200:
            return WorkerResult(provider="reddit", success=True, confidence=0.0, data={})
        children = r.json().get("data", {}).get("children", [])
    return WorkerResult(
        provider="reddit",
        success=True,
        confidence=0.4 if children else 0.0,
        data={"posts": [
            {"title": c["data"].get("title"), "subreddit": c["data"].get("subreddit"),
             "url": "https://reddit.com" + (c["data"].get("permalink") or ""),
             "score": c["data"].get("score")}
            for c in children
        ]},
    )
