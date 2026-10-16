"""Vision provider interface. Any object with `describe(bytes) -> str` is a valid captioner."""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class VisionCaptioner(Protocol):
    def describe(self, image: bytes) -> str:
        """Return a short natural-language description of a JPEG frame. "" if nothing useful."""
        ...
