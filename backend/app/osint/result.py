"""The worker contract. Every worker returns exactly this — never a raw dict.

Backward-compatible with the original 6-field version (provider/success/confidence/latency_ms/data/errors);
adds `cache_hit`, a `failed()` constructor, and `to_dict()` for the JSON edge.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class WorkerResult:
    provider: str
    success: bool = True
    confidence: float = 0.0
    latency_ms: int = 0
    data: dict[str, Any] = field(default_factory=dict)   # provider payload
    errors: list[str] = field(default_factory=list)
    cache_hit: bool = False

    @classmethod
    def failed(cls, provider: str, error: str, latency_ms: int = 0) -> "WorkerResult":
        return cls(provider=provider, success=False, confidence=0.0,
                   latency_ms=latency_ms, errors=[str(error)])

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
