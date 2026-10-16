"""Verify the action-item -> Hermes handoff end-to-end, without a real Hermes install.

Spins up a tiny local HTTP server that impersonates Hermes' task intake, runs the full pipeline with the
REAL HermesOrchestrator pointed at it, and asserts Hermes received the correct JSON + auth. This proves
the wire contract works. Stdlib only: `python3 backend/tests/test_hermes_handoff.py`.
"""
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.memory.store import MemoryStore            # noqa: E402
from app.orchestrator.hermes import HermesOrchestrator  # noqa: E402
from app.pipeline import Pipeline                   # noqa: E402
from app.stt.mock import MockSTT                    # noqa: E402

_received: list[dict] = []


class _StubHermes(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        _received.append(
            {
                "path": self.path,
                "json": json.loads(body),
                "auth": self.headers.get("Authorization"),
            }
        )
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"task_id": "t_123", "status": "queued"}')

    def log_message(self, *args):  # silence the default stderr logging
        pass


def test_hermes_receives_the_action():
    _received.clear()
    server = ThreadingHTTPServer(("127.0.0.1", 0), _StubHermes)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        orch = HermesOrchestrator(f"http://127.0.0.1:{port}", api_key="secret")
        pipe = Pipeline(MockSTT(), MemoryStore(":memory:"), orch)
        result = pipe.process(b"Remind me to email Sam the report tomorrow")

        assert len(_received) == 1, "Hermes should receive exactly one task"
        got = _received[0]
        assert got["path"] == "/tasks", got["path"]
        assert got["json"]["kind"] == "email"
        assert "email Sam" in got["json"]["instruction"]
        assert got["json"]["source"] == "aiglass"
        assert got["auth"] == "Bearer secret", "API key must be sent"

        dispatch = result["actions"][0]["dispatch"]
        assert dispatch["status"] == "accepted" and dispatch["executed"] is True
        assert dispatch["hermes"]["task_id"] == "t_123"
    finally:
        server.shutdown()


def test_unreachable_hermes_does_not_crash_pipeline():
    _received.clear()
    # Nothing is listening on this port -> orchestrator must degrade gracefully.
    orch = HermesOrchestrator("http://127.0.0.1:9", timeout=1.0)
    pipe = Pipeline(MockSTT(), MemoryStore(":memory:"), orch)
    result = pipe.process(b"Remind me to call the dentist")

    dispatch = result["actions"][0]["dispatch"]
    assert dispatch["status"] == "unreachable" and dispatch["executed"] is False
    # The transcript + memory were still captured despite Hermes being down.
    assert result["transcript"]


def _main():
    tests = [test_hermes_receives_the_action, test_unreachable_hermes_does_not_crash_pipeline]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
        except AssertionError as exc:
            failed += 1
            print(f"  FAIL  {t.__name__}: {exc}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_main())
