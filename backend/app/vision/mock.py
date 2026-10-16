"""Deterministic captioner for dev/tests — no ML deps, runs anywhere.

Convention (same as MockSTT): if the payload is valid UTF-8 text, that text IS the caption. Lets tests
drive the vision path without real JPEGs. Otherwise it describes the frame by size.
"""
from __future__ import annotations


class MockVision:
    def describe(self, image: bytes) -> str:
        try:
            return image.decode("utf-8").strip()
        except UnicodeDecodeError:
            return f"a camera frame ({len(image)} bytes)"
