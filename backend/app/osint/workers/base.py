"""Base worker wrapper. A worker is an async fn `(query) -> WorkerResult`; the `@worker(...)` decorator
adds the four cross-cutting guarantees the spec requires:

- timeout  (asyncio.wait_for)
- retry    (exponential backoff on timeouts / network / 429 / 5xx)
- cache    (per (provider, query), TTL)
- logging  (start / finish / latency / error / cache-hit)

The decorator GUARANTEES a WorkerResult is returned — a worker failure never propagates to the engine.
That's what lets the engine stay ignorant of worker internals.
"""
from __future__ import annotations

import asyncio
import functools
import time
from typing import Awaitable, Callable

from ..cache import worker_cache
from ..logging import get_logger
from ..result import WorkerResult
from ..settings import osint_settings

_RETRYABLE = (asyncio.TimeoutError, ConnectionError, OSError)


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, _RETRYABLE):
        return True
    # duck-type httpx errors without importing httpx here
    status = getattr(getattr(exc, "response", None), "status_code", None)
    return status in (429, 500, 502, 503, 504)


def _as_cache_hit(wr: WorkerResult) -> WorkerResult:
    return WorkerResult(provider=wr.provider, success=wr.success, confidence=wr.confidence,
                        latency_ms=wr.latency_ms, data=wr.data, errors=list(wr.errors), cache_hit=True)


def worker(name: str, *, timeout: float | None = None, retries: int | None = None,
           cache: bool = True) -> Callable:
    settings = osint_settings()
    _timeout = settings.worker_timeout if timeout is None else timeout
    _retries = settings.worker_retries if retries is None else retries
    log = get_logger(name)

    def decorator(fn: Callable[..., Awaitable[WorkerResult]]) -> Callable[..., Awaitable[WorkerResult]]:
        @functools.wraps(fn)
        async def wrapped(query: str, **kwargs) -> WorkerResult:
            ck = (name, query.strip().lower())
            if cache and ck in worker_cache:
                log.info("cache_hit query=%r", query)
                return _as_cache_hit(worker_cache[ck])

            start = time.perf_counter()
            log.info("start query=%r", query)
            last_err = "unknown error"
            for attempt in range(_retries + 1):
                try:
                    result = await asyncio.wait_for(fn(query, **kwargs), timeout=_timeout)
                    if not isinstance(result, WorkerResult):
                        result = WorkerResult(provider=name, success=True, data=dict(result or {}))
                    if not result.provider:
                        result.provider = name
                    result.latency_ms = int((time.perf_counter() - start) * 1000)
                    log.info("finish success=%s latency_ms=%d", result.success, result.latency_ms)
                    if cache and result.success:
                        worker_cache[ck] = result
                    return result
                except Exception as exc:  # noqa: BLE001 — a worker must never raise to the engine
                    last_err = f"{type(exc).__name__}: {exc}"
                    if attempt < _retries and _is_retryable(exc):
                        backoff = settings.worker_backoff * (2 ** attempt)
                        log.warning("retry attempt=%d in %.2fs err=%s", attempt + 1, backoff, last_err)
                        await asyncio.sleep(backoff)
                        continue
                    log.error("failed err=%s", last_err)
                    break
            return WorkerResult.failed(name, last_err, int((time.perf_counter() - start) * 1000))

        wrapped._worker_name = name   # registry discovery marker
        return wrapped

    return decorator
