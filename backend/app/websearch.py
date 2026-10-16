import time

import httpx

from .config import load_settings


TAVILY_URL = "https://api.tavily.com/search"


async def public_search(
    query: str,
    max_results: int = 5,
) -> dict:

    settings = load_settings()

    if not settings.tavily_api_key:
        raise RuntimeError("TAVILY_API_KEY not configured")

    api_key = settings.tavily_api_key

    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "advanced",
        "include_answer": True,
        "include_images": False,
        "include_raw_content": False,
        "max_results": max_results,
    }

    start = time.perf_counter()

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            TAVILY_URL,
            json=payload,
        )

        response.raise_for_status()

        data = response.json()

    latency = int((time.perf_counter() - start) * 1000)

    return {
        "query": query,
        "latency_ms": latency,
        "answer": data.get("answer"),
        "results": data.get("results", []),
    }
