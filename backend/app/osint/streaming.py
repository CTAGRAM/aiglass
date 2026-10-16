"""Streaming variant of the engine: yields progress events as workers finish, for websocket clients.

    Searching memory... / Searching github... / github: ok / Resolved ... / Confidence 0.8 / Summary ready.

The FastAPI edge can forward these straight over a WebSocket (see app/main.py ws route).
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import asdict, dataclass, field
from typing import AsyncIterator

from . import registry
from .logging import get_logger
from .merger import merge
from .planner import plan
from .resolver import resolve
from .scorer import score

log = get_logger("streaming")


@dataclass
class StreamEvent:
    phase: str                          # plan | worker | worker_done | resolve | score | done
    message: str
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


async def run_streaming(query: str) -> AsyncIterator[dict]:
    start = time.perf_counter()

    names = plan(query)
    yield StreamEvent("plan", f"Planning: {', '.join(names) or 'none'}", {"workers": names}).to_dict()

    chosen = registry.resolve_workers(names)
    for name, _ in chosen:
        yield StreamEvent("worker", f"Searching {name}...", {"worker": name}).to_dict()

    results = []
    tasks = [asyncio.create_task(fn(query)) for _, fn in chosen]
    for coro in asyncio.as_completed(tasks):
        r = await coro
        results.append(r)
        yield StreamEvent(
            "worker_done",
            f"{r.provider}: {'ok' if r.success else 'no result'}",
            {"worker": r.provider, "success": r.success, "latency_ms": r.latency_ms},
        ).to_dict()

    person = resolve(results)
    yield StreamEvent("resolve", f"Resolved {person.name or person.github or 'unknown'}").to_dict()

    merged = merge(query, results)
    confidence = score(results)
    person.confidence = confidence
    yield StreamEvent("score", f"Confidence {confidence}", {"confidence": confidence}).to_dict()

    result = {
        "query": query,
        "person": person.to_dict(),
        "summary": merged.get("summary") or person.bio or person.name or "No confident match found.",
        "confidence": confidence,
        "sources": merged["sources"],
        "matches": merged["matches"],
        "workers_used": [r.provider for r in results],
        "latency_ms": int((time.perf_counter() - start) * 1000),
    }
    yield StreamEvent("done", "Summary ready.", result).to_dict()
