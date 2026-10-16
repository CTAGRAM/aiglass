"""Hermes orchestrator client.

Hands action items to a running Hermes Agent (self-hosted on your VPS, sandboxed) over HTTP. Uses only
the stdlib (urllib) so it adds no dependency, and it degrades gracefully — if Hermes is unreachable the
action is queued/reported rather than crashing the capture pipeline.

Point HERMES_URL at your Hermes gateway's task intake endpoint. OpenClaw can be swapped in by writing an
analogous client with the same `dispatch` signature.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from ..actions import ActionItem


class HermesOrchestrator:
    def __init__(self, base_url: str, api_key: str | None = None, timeout: float = 5.0) -> None:
        self._url = base_url.rstrip("/") + "/tasks"
        self._api_key = api_key
        self._timeout = timeout

    def dispatch(self, action: ActionItem) -> dict:
        payload = json.dumps(
            {"instruction": action.text, "kind": action.kind, "source": "aiglass"}
        ).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        req = urllib.request.Request(self._url, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                body = resp.read().decode("utf-8") or "{}"
                return {"status": "accepted", "executed": True, "hermes": json.loads(body)}
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            # Never let orchestrator downtime break capture — surface it instead.
            return {"status": "unreachable", "executed": False, "error": str(exc), "text": action.text}
