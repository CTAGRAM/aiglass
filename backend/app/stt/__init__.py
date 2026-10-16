"""Speech-to-text providers. Mock is the stdlib-only default; Whisper is optional."""
from .base import STT
from .mock import MockSTT

__all__ = ["STT", "MockSTT"]
