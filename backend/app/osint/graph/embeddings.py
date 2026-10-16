"""Embeddings for semantic search over the graph.

`Embedder` is the interface; `HashEmbedder` is a dependency-free fallback so semantic search *works*
(deterministic cosine similarity) without a model. Plug OpenAI / sentence-transformers behind the same
interface later — nothing else changes.
"""
from __future__ import annotations

import hashlib
import math
from typing import Protocol, runtime_checkable


@runtime_checkable
class Embedder(Protocol):
    def embed(self, text: str) -> list[float]: ...


class HashEmbedder:
    """Bag-of-hashed-tokens unit vector. Not model-quality, but real, fast, and zero-dep."""

    def __init__(self, dim: int = 128) -> None:
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        v = [0.0] * self.dim
        for tok in text.lower().split():
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            v[h % self.dim] += 1.0
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))
