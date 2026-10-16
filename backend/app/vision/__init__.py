"""Vision captioning for camera frames. Mock is the stdlib-only default; LLM is optional."""
from .base import VisionCaptioner
from .mock import MockVision

__all__ = ["VisionCaptioner", "MockVision"]
