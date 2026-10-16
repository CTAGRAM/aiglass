"""Confidence scorer.

Confidence blends: source quality (how trustworthy the provider is), worker self-confidence, and
corroboration (multiple agreeing sources raise it). Kept simple and deterministic.

`merge_results` is retained as a backward-compatible entry point (merge + score in the original shape).
"""
from __future__ import annotations

from typing import Any

from .merger import merge
from .result import WorkerResult

_SOURCE_QUALITY = {
    "memory": 1.0,
    "github": 0.9,
    "website": 0.7,
    "tavily": 0.75,
    "company": 0.7,
    "conference": 0.6,
    "hackernews": 0.55,
    "youtube": 0.5,
    "reddit": 0.45,
    "podcast": 0.4,
}
_IDENTITY_PROVIDERS = {"github"}   # sources that confirm identity by exact match


def score(results: list[WorkerResult]) -> float:
    # Only sources that actually found something count (confidence > 0). An empty-but-successful worker
    # (e.g. github with no match) contributes nothing — it must not inflate the score.
    useful = [r for r in results if isinstance(r, WorkerResult) and r.success and r.confidence > 0]
    if not useful:
        return 0.0
    weighted = [_SOURCE_QUALITY.get(r.provider, 0.5) * r.confidence for r in useful]
    base = sum(weighted) / len(weighted)
    corroboration = 0.05 * (len(useful) - 1)          # multiple agreeing sources raise confidence
    identity = 0.15 if any(
        r.provider in _IDENTITY_PROVIDERS and (r.data.get("username") or r.data.get("name"))
        for r in useful
    ) else 0.0                                          # a confirmed identity is strong evidence
    return round(min(1.0, base + corroboration + identity), 2)


def merge_results(query: str, workers: list[Any]) -> dict:
    """Backward-compatible: merge + score in the pre-refactor return shape."""
    wrs = [w for w in workers if isinstance(w, WorkerResult)]
    merged = merge(query, wrs)
    return {
        "query": query,
        "confidence": score(wrs),
        "summary": merged["summary"],
        "sources": merged["sources"],
        "matches": merged["matches"],
    }
