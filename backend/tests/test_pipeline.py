"""End-to-end test of the capture -> STT -> memory -> action -> orchestrator loop.

Runs with zero dependencies: `python3 backend/tests/test_pipeline.py` (also works under pytest).
Uses MockSTT (treats UTF-8 payload as the transcript) + in-memory SQLite + MockOrchestrator.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.memory.store import MemoryStore          # noqa: E402
from app.orchestrator.mock import MockOrchestrator  # noqa: E402
from app.pipeline import Pipeline                  # noqa: E402
from app.stt.mock import MockSTT                   # noqa: E402


def _build():
    mem = MemoryStore(":memory:")
    orch = MockOrchestrator()
    pipe = Pipeline(MockSTT(), mem, orch)
    return pipe, mem, orch


def test_action_is_extracted_stored_and_dispatched():
    pipe, mem, orch = _build()
    result = pipe.process(b"Remind me to email Sam about the invoice tomorrow")

    assert result["transcript"].startswith("Remind me to email Sam")
    assert len(result["actions"]) == 1, "one action item expected"
    assert result["actions"][0]["action"]["kind"] == "email", "should classify as email"

    # transcript persisted
    assert len(mem.recent_transcripts()) == 1
    # memory row created for the action item
    assert len(mem.memories(kind="action_item")) == 1
    # orchestrator actually received it
    assert len(orch.dispatched) == 1
    assert orch.dispatched[0].kind == "email"


def test_plain_sentence_creates_no_action():
    pipe, mem, orch = _build()
    result = pipe.process(b"The sky is blue and the coffee is warm")

    assert result["transcript"]
    assert result["actions"] == []
    assert len(mem.recent_transcripts()) == 1      # transcript still stored
    assert mem.memories(kind="action_item") == []
    assert orch.dispatched == []


def test_multiple_actions_and_search():
    pipe, mem, orch = _build()
    pipe.process(b"I need to buy milk. Also schedule a dentist appointment. Nice weather today.")

    kinds = sorted(a.kind for a in orch.dispatched)
    assert kinds == ["buy", "schedule"], f"expected buy+schedule, got {kinds}"

    hits = mem.search_memories("dentist")
    assert len(hits) == 1 and "dentist" in hits[0].text.lower()


def test_empty_transcript_is_noop():
    pipe, mem, orch = _build()
    result = pipe.process(b"   ")
    assert result["actions"] == []
    assert mem.recent_transcripts() == []


def _main():
    tests = [
        test_action_is_extracted_stored_and_dispatched,
        test_plain_sentence_creates_no_action,
        test_multiple_actions_and_search,
        test_empty_transcript_is_noop,
    ]
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
