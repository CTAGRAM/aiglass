"""In-memory orchestrator: records dispatched actions instead of executing them. For dev/tests."""
from __future__ import annotations

from ..actions import ActionItem


class MockOrchestrator:
    def __init__(self) -> None:
        self.dispatched: list[ActionItem] = []

    def dispatch(self, action: ActionItem) -> dict:
        self.dispatched.append(action)
        return {"status": "accepted", "kind": action.kind, "text": action.text, "executed": False}
