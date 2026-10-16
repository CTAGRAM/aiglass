"""Camera-frame path: a JPEG frame -> caption -> searchable 'observation' memory.

Uses MockVision (treats a UTF-8 payload as the caption) so it runs with zero deps.
`python3 backend/tests/test_vision.py`
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.memory.store import MemoryStore          # noqa: E402
from app.orchestrator.mock import MockOrchestrator  # noqa: E402
from app.pipeline import Pipeline                  # noqa: E402
from app.stt.mock import MockSTT                   # noqa: E402
from app.vision.mock import MockVision             # noqa: E402


def _build(with_vision=True):
    mem = MemoryStore(":memory:")
    vision = MockVision() if with_vision else None
    return Pipeline(MockSTT(), mem, MockOrchestrator(), vision=vision), mem


def test_frame_becomes_observation_memory():
    pipe, mem = _build()
    result = pipe.process_frame(b"a red stop sign at the corner")
    assert result["caption"] == "a red stop sign at the corner"
    obs = mem.memories(kind="observation")
    assert len(obs) == 1 and "stop sign" in obs[0].text
    assert obs[0].source == "camera"


def test_observation_is_searchable():
    pipe, mem = _build()
    pipe.process_frame(b"a poster advertising a concert on Friday night")
    hits = mem.search_memories("concert")
    assert len(hits) == 1 and "Friday" in hits[0].text


def test_pipeline_without_vision_is_safe():
    pipe, mem = _build(with_vision=False)
    result = pipe.process_frame(b"anything at all")
    assert result["caption"] == "" and result["memory_id"] is None
    assert mem.memories(kind="observation") == []


def _main():
    tests = [
        test_frame_becomes_observation_memory,
        test_observation_is_searchable,
        test_pipeline_without_vision_is_safe,
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
