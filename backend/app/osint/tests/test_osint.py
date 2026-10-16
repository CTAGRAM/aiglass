"""Unit + integration tests for the profile enrichment engine.

Runs with zero third-party deps (cache falls back to stdlib; network workers are skipped/graceful).
    python3 app/osint/tests/test_osint.py       # from backend/
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))  # -> backend/

from app.osint import engine, merger, planner, registry, resolver, scorer  # noqa: E402
from app.osint.result import WorkerResult                                    # noqa: E402
from app.osint.workers.base import worker                                    # noqa: E402


# ---- base worker: normalization, cache, timeout, never-raises ----
def test_base_success_and_cache():
    calls = {"n": 0}

    @worker("dummy_ok", timeout=2, retries=0)
    async def w(query: str) -> WorkerResult:
        calls["n"] += 1
        return WorkerResult(provider="dummy_ok", success=True, confidence=0.5, data={"q": query})

    async def run():
        r1 = await w("abc")
        assert isinstance(r1, WorkerResult) and r1.success and not r1.cache_hit
        assert r1.latency_ms >= 0
        r2 = await w("abc")
        assert r2.cache_hit is True
        assert calls["n"] == 1          # served from cache the 2nd time

    asyncio.run(run())


def test_base_timeout_returns_failed():
    @worker("dummy_slow", timeout=0.05, retries=0)
    async def w(query: str) -> WorkerResult:
        await asyncio.sleep(1)
        return WorkerResult(provider="dummy_slow")

    async def run():
        r = await w("x")
        assert isinstance(r, WorkerResult) and r.success is False and r.errors

    asyncio.run(run())


def test_base_never_raises():
    @worker("dummy_boom", timeout=2, retries=0)
    async def w(query: str) -> WorkerResult:
        raise ValueError("boom")

    async def run():
        r = await w("x")
        assert r.success is False and "boom" in r.errors[0]

    asyncio.run(run())


# ---- planner heuristics ----
def test_planner():
    assert "memory" in planner.plan("anyone")
    assert "tavily" in planner.plan("anyone")
    assert "github" in planner.plan("a react typescript developer")
    assert "github" not in planner.plan("a chef in paris")


# ---- registry ----
def test_registry_discovers_memory():
    assert "memory" in registry.available()


def test_registry_execute_isolated():
    async def run():
        results = await registry.execute(["memory", "does_not_exist"], "nobody")
        assert all(isinstance(r, WorkerResult) for r in results)
        assert any(r.provider == "memory" for r in results)

    asyncio.run(run())


# ---- resolver ----
def test_resolver_builds_person():
    gh = WorkerResult(provider="github", success=True, confidence=0.9, data={
        "name": "Guillermo Rauch", "username": "rauchg", "company": "Vercel",
        "bio": "creator of Next.js", "location": "SF", "blog": "https://rauchg.com",
        "languages": {"TypeScript": 3}, "repos": [{"name": "next.js"}]})
    p = resolver.resolve([gh])
    assert p.name == "Guillermo Rauch" and p.github == "rauchg" and p.company == "Vercel"
    assert p.attributes.get("languages") == {"TypeScript": 3}
    assert p.id == "person:rauchg"


# ---- merger + scorer ----
def test_merger_and_scorer():
    rs = [
        WorkerResult(provider="github", success=True, confidence=0.9, data={"name": "x"}),
        WorkerResult(provider="tavily", success=True, confidence=0.75,
                     data={"answer": "hi", "results": [{"title": "t", "url": "u", "score": 0.9}]}),
    ]
    merged = merger.merge("x", rs)
    assert merged["summary"] == "hi" and len(merged["matches"]) == 1
    assert len(merged["sources"]) == 2
    c = scorer.score(rs)
    assert 0.0 < c <= 1.0
    assert scorer.score([]) == 0.0


# ---- engine end-to-end (memory only; no network needed) ----
def test_engine_end_to_end_and_cache():
    async def run():
        out = await engine.run("some unlikely name zzz")
        for k in ("query", "person", "summary", "confidence", "sources", "workers_used", "latency_ms"):
            assert k in out, k
        assert out["cache_hit"] is False
        # low-confidence misses are NOT cached (so they retry as sources recover)
        out2 = await engine.run("some unlikely name zzz")
        assert out2["cache_hit"] is False
        # confident results ARE served from cache
        from app.osint.cache import entity_cache
        entity_cache["seeded person q"] = {"query": "seeded person q", "confidence": 0.9, "cache_hit": False}
        cached = await engine.run("Seeded Person Q")
        assert cached["cache_hit"] is True

    asyncio.run(run())


def _main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL  {t.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"  ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_main())
