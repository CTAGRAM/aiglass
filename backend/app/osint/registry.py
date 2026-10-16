"""Dynamic worker registry.

Discovers every `@worker`-decorated coroutine under `app.osint.workers.*` and executes a requested subset
in parallel with per-worker isolation. Adding a worker file requires ZERO edits here or in the engine.
A worker whose optional dependency is missing (e.g. httpx) is skipped, not fatal.
"""
from __future__ import annotations

import asyncio
import importlib
import pkgutil
from typing import Awaitable, Callable

from . import workers as _workers_pkg
from .logging import get_logger
from .result import WorkerResult

log = get_logger("registry")

_REGISTRY: dict[str, Callable[..., Awaitable[WorkerResult]]] = {}


def _discover() -> dict[str, Callable[..., Awaitable[WorkerResult]]]:
    if _REGISTRY:
        return _REGISTRY
    for mod in pkgutil.iter_modules(_workers_pkg.__path__):
        if mod.name.startswith("_") or mod.name == "base":
            continue
        try:
            module = importlib.import_module(f"{_workers_pkg.__name__}.{mod.name}")
        except Exception as exc:  # a worker with a missing dep must not break discovery
            log.warning("skip worker module %s: %s", mod.name, exc)
            continue
        for obj in vars(module).values():
            wname = getattr(obj, "_worker_name", None)
            if wname:
                _REGISTRY[wname] = obj
    log.info("discovered workers: %s", sorted(_REGISTRY))
    return _REGISTRY


def available() -> list[str]:
    return sorted(_discover())


def resolve_workers(names: list[str]) -> list[tuple[str, Callable[..., Awaitable[WorkerResult]]]]:
    """Return (name, fn) pairs for the requested, available workers — used by the streaming engine."""
    reg = _discover()
    return [(n, reg[n]) for n in names if n in reg]


async def execute(names: list[str], query: str) -> list[WorkerResult]:
    """Run the named workers concurrently. Failure/absence of one never fails the lookup."""
    reg = _discover()
    chosen = [(n, reg[n]) for n in names if n in reg]
    for missing in (n for n in names if n not in reg):
        log.warning("planned worker not available: %s", missing)

    raw = await asyncio.gather(*(fn(query) for _, fn in chosen), return_exceptions=True)

    out: list[WorkerResult] = []
    for (name, _), res in zip(chosen, raw):
        if isinstance(res, WorkerResult):
            out.append(res)
        else:  # the base decorator should prevent this; belt-and-suspenders
            out.append(WorkerResult.failed(name, f"{type(res).__name__}: {res}"))
    return out
