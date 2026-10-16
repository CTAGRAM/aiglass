"""Website worker — if the query contains a domain/URL, fetch it and extract <title> + meta description."""
from __future__ import annotations

import re

import httpx

from ..result import WorkerResult
from .base import worker

_DOMAIN = re.compile(r"\b([a-z0-9-]+\.[a-z]{2,})(/\S*)?", re.I)
_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
_DESC = re.compile(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', re.I | re.S)


@worker("website", timeout=10)
async def website_worker(query: str) -> WorkerResult:
    q = query.strip()
    if q.startswith("http://") or q.startswith("https://"):
        url = q
    else:
        m = _DOMAIN.search(q)
        if not m:
            return WorkerResult(provider="website", success=True, confidence=0.0, data={})
        url = "https://" + m.group(0)

    async with httpx.AsyncClient(timeout=8, follow_redirects=True,
                                 headers={"User-Agent": "AIGlass"}) as client:
        r = await client.get(url)
        html = r.text[:20000]

    tm = _TITLE.search(html)
    dm = _DESC.search(html)
    title = tm.group(1).strip() if tm else ""
    description = dm.group(1).strip() if dm else ""
    return WorkerResult(
        provider="website",
        success=True,
        confidence=0.6 if title else 0.0,
        data={"url": url, "title": title, "description": description},
    )
