"""YouTube worker — YouTube Data API v3. Real when YOUTUBE_API_KEY is set, else graceful."""
from __future__ import annotations

import os

import httpx

from ..result import WorkerResult
from .base import worker

API = "https://www.googleapis.com/youtube/v3/search"


@worker("youtube", timeout=10)
async def youtube_worker(query: str) -> WorkerResult:
    key = os.getenv("YOUTUBE_API_KEY", "")
    if not key:
        return WorkerResult.failed("youtube", "YOUTUBE_API_KEY not configured")
    async with httpx.AsyncClient(timeout=8) as client:
        r = await client.get(API, params={
            "key": key, "q": query, "part": "snippet", "type": "video", "maxResults": 5,
        })
        r.raise_for_status()
        items = r.json().get("items", [])
    return WorkerResult(
        provider="youtube",
        success=True,
        confidence=0.4 if items else 0.0,
        data={"videos": [
            {"title": i["snippet"]["title"], "channel": i["snippet"]["channelTitle"],
             "videoId": i["id"].get("videoId")}
            for i in items
        ]},
    )
