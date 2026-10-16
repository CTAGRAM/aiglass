"""Multi-level TTL cache: worker results, resolved entities, summaries.

Uses `cachetools` when installed; otherwise a small thread-safe stdlib fallback so the core + tests run
with zero third-party deps. `person_cache` is kept as a backward-compatible alias of the entity cache.
"""
from __future__ import annotations

import threading
import time
from typing import Any

try:
    from cachetools import TTLCache as _TTLCache  # type: ignore
except Exception:  # pragma: no cover - exercised only when cachetools is absent
    class _TTLCache:
        """Minimal thread-safe TTL cache with the subset of the cachetools API we use."""

        def __init__(self, maxsize: int = 500, ttl: float = 600) -> None:
            self.maxsize = maxsize
            self.ttl = ttl
            self._d: dict[Any, tuple[float, Any]] = {}
            self._lock = threading.Lock()

        def _expired(self, ts: float) -> bool:
            return (time.monotonic() - ts) > self.ttl

        def __contains__(self, key: Any) -> bool:
            with self._lock:
                item = self._d.get(key)
                if item is None:
                    return False
                if self._expired(item[0]):
                    del self._d[key]
                    return False
                return True

        def __getitem__(self, key: Any) -> Any:
            with self._lock:
                ts, val = self._d[key]
                if self._expired(ts):
                    del self._d[key]
                    raise KeyError(key)
                return val

        def __setitem__(self, key: Any, val: Any) -> None:
            with self._lock:
                if len(self._d) >= self.maxsize and key not in self._d:
                    self._d.pop(next(iter(self._d)))
                self._d[key] = (time.monotonic(), val)

        def get(self, key: Any, default: Any = None) -> Any:
            try:
                return self[key]
            except KeyError:
                return default


from .settings import osint_settings  # noqa: E402

_s = osint_settings()

worker_cache = _TTLCache(maxsize=2000, ttl=_s.worker_cache_ttl)
entity_cache = _TTLCache(maxsize=1000, ttl=_s.entity_cache_ttl)
summary_cache = _TTLCache(maxsize=1000, ttl=_s.summary_cache_ttl)

# Backward-compat: the original engine cache was named `person_cache`.
person_cache = entity_cache
