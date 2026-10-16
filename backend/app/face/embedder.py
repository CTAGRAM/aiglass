"""Face embedding providers. Every embedder: `embed(image_bytes) -> list[float] | None` where None means
no face was detected. Embeddings are L2-normalized unit vectors so cosine similarity = dot product.
"""
from __future__ import annotations

import hashlib
import math
import os
from typing import Protocol, runtime_checkable


@runtime_checkable
class Embedder(Protocol):
    dim: int
    def embed(self, image_bytes: bytes) -> list[float] | None: ...


class MockEmbedder:
    """Deterministic pseudo-embedding from the image bytes. NOT real face recognition — for tests/dev and
    as a safe default. Same bytes -> same (zero-centered, normalized) vector, so identical inputs match and
    different inputs are ~orthogonal."""

    dim = 64

    def embed(self, image_bytes: bytes) -> list[float] | None:
        if not image_bytes:
            return None
        h = hashlib.shake_256(image_bytes).digest(self.dim)
        v = [b / 255.0 - 0.5 for b in h]           # zero-center so distinct inputs are ~orthogonal
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / n for x in v]


class InsightFaceEmbedder:
    """Real face embedding via InsightFace (ONNX Runtime, CPU). Detects the largest face and returns its
    512-d normed embedding. Heavy deps are imported lazily so this module always loads.

    Install (server):  pip install insightface onnxruntime opencv-python-headless numpy
    """

    dim = 512

    def __init__(self, model_name: str = "buffalo_s") -> None:
        from insightface.app import FaceAnalysis  # optional heavy dependency
        self._app = FaceAnalysis(name=model_name, providers=["CPUExecutionProvider"])
        self._app.prepare(ctx_id=-1, det_size=(320, 320))

    def embed(self, image_bytes: bytes) -> list[float] | None:
        import cv2
        import numpy as np
        arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return None
        faces = self._app.get(img)
        if not faces:
            return None
        face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
        return face.normed_embedding.tolist()


def build_embedder() -> Embedder:
    if os.getenv("FACE_EMBEDDER", "mock") == "insightface":
        return InsightFaceEmbedder(os.getenv("FACE_MODEL", "buffalo_s"))
    return MockEmbedder()
