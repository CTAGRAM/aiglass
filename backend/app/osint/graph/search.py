"""Search over the knowledge graph: keyword recall (store-native) + optional embedding re-ranking."""
from __future__ import annotations

from .embeddings import Embedder, HashEmbedder, cosine


def semantic_rerank(query: str, entities: list[dict], embedder: Embedder | None = None) -> list[dict]:
    """Re-rank candidate entities by semantic similarity to the query."""
    embedder = embedder or HashEmbedder()
    qv = embedder.embed(query)
    scored: list[tuple[float, dict]] = []
    for e in entities:
        text = f"{e.get('name', '')} {' '.join(str(v) for v in (e.get('attributes') or {}).values())}"
        scored.append((cosine(qv, embedder.embed(text)), e))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [e for _, e in scored]
