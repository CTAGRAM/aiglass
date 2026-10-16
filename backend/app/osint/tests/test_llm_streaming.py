"""LLM-fallback + streaming + worker-registration tests. Zero deps (LLM falls back with no key configured).
    python3 app/osint/tests/test_llm_streaming.py       # from backend/
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))  # -> backend/

from app.osint import planner, registry, streaming                 # noqa: E402
from app.osint.llm import planner as llm_planner                    # noqa: E402
from app.osint.llm import summarizer, verifier                     # noqa: E402


def test_summarizer_fallback():
    async def run():
        s = await summarizer.summarize(
            {"person": {"name": "Ada Lovelace", "company": "Analytical Engine", "bio": "mathematician"}}
        )
        assert "Ada Lovelace" in s
    asyncio.run(run())


def test_planner_llm_fallback():
    async def run():
        picks = await llm_planner.plan_llm("a react typescript developer", ["memory", "github", "tavily"])
        assert "memory" in picks and "github" in picks
        assert all(p in ("memory", "github", "tavily") for p in picks)
    asyncio.run(run())


def test_verifier_fallback():
    async def run():
        out = await verifier.verify(["the sky is blue"])
        assert out and out[0]["claim"] == "the sky is blue" and out[0]["verified"] is None
        assert await verifier.verify([]) == []
    asyncio.run(run())


def test_streaming_emits_phases():
    async def run():
        events = [e async for e in streaming.run_streaming("some unlikely person qqq")]
        phases = [e["phase"] for e in events]
        assert phases[0] == "plan" and phases[-1] == "done"
        assert "resolve" in phases and "score" in phases
        assert events[-1]["data"].get("query") == "some unlikely person qqq"
    asyncio.run(run())


def test_new_workers_registered():
    avail = registry.available()
    for w in ("conference", "email", "calendar", "docs", "local"):   # graceful (no httpx) -> discoverable
        assert w in avail, w


def test_planner_routes_new_sources():
    assert "hackernews" in planner.plan("a rust developer")
    assert "youtube" in planner.plan("best tutorial video on x")
    assert "podcast" in planner.plan("the x podcast episode")
    assert "website" in planner.plan("check example.com please")
    assert "calendar" in planner.plan("my meeting schedule")


def _main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"  FAIL  {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_main())
