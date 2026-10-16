"""Orchestrator interface. Anything with `dispatch(ActionItem) -> dict` is a valid action brain,
so Hermes and OpenClaw are interchangeable behind this seam."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..actions import ActionItem


@runtime_checkable
class Orchestrator(Protocol):
    def dispatch(self, action: ActionItem) -> dict:
        """Hand an action item to the agent brain. Return a status dict (never raises)."""
        ...
