"""STT provider interface. Any object with `transcribe(bytes) -> str` is a valid provider."""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class STT(Protocol):
    def transcribe(self, audio: bytes) -> str:
        """Turn a chunk of audio into text. Return "" for silence/no speech."""
        ...
