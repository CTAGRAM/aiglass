"""Company / general-entity enrichment via Wikipedia's public REST summary API (no key required)."""
from __future__ import annotations

import urllib.parse

import httpx

from ..result import WorkerResult
from .base import worker

WIKI = "https://en.wikipedia.org/api/rest_v1/page/summary/"


@worker("company", timeout=10)
async def company_worker(query: str) -> WorkerResult:
    title = urllib.parse.quote(query.strip().replace(" ", "_"))
    async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
        r = await client.get(WIKI + title, headers={"User-Agent": "AIGlass"})
    if r.status_code != 200:
        return WorkerResult(provider="company", success=True, confidence=0.0, data={})
    d = r.json()
    if d.get("type") == "disambiguation" or not d.get("extract"):
        return WorkerResult(provider="company", success=True, confidence=0.0, data={})
    return WorkerResult(
        provider="company",
        success=True,
        confidence=0.6,
        data={
            "title": d.get("title"),
            "description": d.get("description"),
            "extract": d.get("extract"),
            "url": (d.get("content_urls") or {}).get("desktop", {}).get("page"),
        },
    )
