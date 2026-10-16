"""Deterministic STT for dev/tests — no ML deps, runs anywhere (incl. Python 3.14).

Convention: if the audio payload is valid UTF-8 text, it IS the transcript. This lets tests and the
companion app's "type instead of speak" mode drive the whole pipeline without real audio.
"""
from __future__ import annotations


class MockSTT:
    def __init__(self, fallback: str = "hello, this is a mock transcript") -> None:
        self._fallback = fallback

    def transcribe(self, audio: bytes) -> str:
        try:
            text = audio.decode("utf-8")
        except UnicodeDecodeError:
            return self._fallback
        return text.strip()
