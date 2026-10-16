"""Evidence merger — flattens WorkerResults into a summary + source list + ranked matches.

Separated from the scorer per the spec: the merger assembles *what we found*; the scorer judges *how much
to trust it*.
"""
from __future__ import annotations

from .result import WorkerResult


def merge(query: str, results: list[WorkerResult]) -> dict:
    summary = ""
    sources: list[dict] = []
    matches: list[dict] = []

    for r in results:
        if not isinstance(r, WorkerResult):
            continue
        sources.append({
            "provider": r.provider,
            "success": r.success,
            "latency_ms": r.latency_ms,
            "cache_hit": r.cache_hit,
        })
        d = r.data or {}
        if r.provider == "tavily" and r.success:
            if d.get("answer"):
                summary = d["answer"]
            for res in d.get("results", []):
                matches.append({
                    "title": res.get("title"),
                    "url": res.get("url"),
                    "score": res.get("score"),
                })
        elif r.provider == "company" and r.success and d.get("extract") and not summary:
            summary = d["extract"]

    return {"summary": summary, "sources": sources, "matches": matches}
