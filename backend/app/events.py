"""In-process real-time event hub — the sync spine for the dual-brain setup.

Both brains write to one shared memory (SQLite/pgvector) and both observe one live event stream:
- **Gemini Live** (fast reflex, app-side) logs each conversation turn here.
- **Hermes** (durable memory + action, VPS-side) reads the same history and pushes results back.

Anything published here is fanned out to every `/ws/events` subscriber, so the glasses app, a dashboard,
and Hermes all see new turns/observations/action-results the moment they happen.

This is a single-process fan-out (asyncio, stdlib). For multi-process / multi-VPS deployments, swap the
body of `publish` for a Redis pub/sub channel — the interface stays identical.
"""
from __future__ import annotations

import asyncio


class EventHub:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.discard(q)

    async def publish(self, event: dict) -> None:
        # Non-blocking fan-out: a slow subscriber never stalls the others or the caller.
        for q in list(self._subscribers):
            q.put_nowait(event)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)
