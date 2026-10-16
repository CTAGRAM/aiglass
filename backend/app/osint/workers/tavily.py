"""Tavily worker — public web search with an answer + ranked results."""
from __future__ import annotations

import httpx

from ...config import load_settings
from ..result import WorkerResult
from .base import worker

TAVILY_URL = "https://api.tavily.com/search"


@worker("tavily", timeout=18)
async def tavily_worker(query: str, max_results: int = 5) -> WorkerResult:
    settings = load_settings()
    if not settings.tavily_api_key:
        return WorkerResult.failed("tavily", "TAVILY_API_KEY not configured")

    payload = {
        "api_key": settings.tavily_api_key,
        "query": query,
        "search_depth": "advanced",
        "include_answer": True,
        "include_images": False,
        "include_raw_content": False,
        "max_results": max_results,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(TAVILY_URL, json=payload)
        response.raise_for_status()
        data = response.json()

    return WorkerResult(
        provider="tavily",
        success=True,
        confidence=0.75,
        data={"answer": data.get("answer", ""), "results": data.get("results", [])},
    )
