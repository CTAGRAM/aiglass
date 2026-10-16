"""Regression tests for the planner/resolver/scorer correctness fixes.
    python3 app/osint/tests/test_correctness.py       # from backend/
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))  # -> backend/

from app.osint import planner, resolver, scorer          # noqa: E402
from app.osint.result import WorkerResult                # noqa: E402
from app.osint.workers.github import _search_term        # noqa: E402


def test_planner_schedules_github_for_usernames_and_names():
    for q in ("rauchg", "@rauchg", "github.com/rauchg", "Guillermo Rauch", "vercel"):
        assert "github" in planner.plan(q), q
    # queries with stopwords are not treated as names
    assert "github" not in planner.plan("a chef in paris")


def test_github_search_term_normalizes_handles():
    assert _search_term("rauchg") == "rauchg"
    assert _search_term("@rauchg") == "rauchg"
    assert _search_term("https://github.com/rauchg") == "rauchg"
    assert _search_term("github.com/rauchg/next.js") == "rauchg"


def test_resolver_maps_github_identity_fully():
    gh = WorkerResult(provider="github", success=True, confidence=0.9, data={
        "username": "rauchg", "name": "Guillermo Rauch", "company": "Vercel",
        "bio": "creator of Next.js", "location": "SF", "blog": "https://rauchg.com",
        "followers": 50000, "public_repos": 300,
        "languages": {"TypeScript": 5}, "repos": [{"name": "next.js"}]})
    p = resolver.resolve([gh])
    assert p.name == "Guillermo Rauch"
    assert p.github == "rauchg"
    assert p.company == "Vercel"
    assert p.website == "https://rauchg.com"
    assert p.location == "SF"
    assert p.attributes["followers"] == 50000
    assert p.attributes["public_repos"] == 300
    assert p.id == "person:rauchg"


def test_scorer_rewards_identity_and_ignores_empties():
    # empty-but-successful workers (confidence 0) must not inflate the score
    empties = [WorkerResult(provider="memory", success=True, confidence=0.0, data={}),
               WorkerResult(provider="company", success=True, confidence=0.0, data={})]
    assert scorer.score(empties) == 0.0

    # a confirmed GitHub identity + agreeing web search scores high (target ~0.9)
    strong = [
        WorkerResult(provider="github", success=True, confidence=0.9,
                     data={"username": "rauchg", "name": "Guillermo Rauch"}),
        WorkerResult(provider="tavily", success=True, confidence=0.75, data={"answer": "..."}),
    ]
    c_strong = scorer.score(strong)
    assert c_strong >= 0.85, c_strong

    # same evidence WITHOUT an identity source scores lower
    no_identity = [
        WorkerResult(provider="tavily", success=True, confidence=0.75, data={"answer": "..."}),
        WorkerResult(provider="company", success=True, confidence=0.6, data={"extract": "..."}),
    ]
    assert scorer.score(no_identity) < c_strong


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
