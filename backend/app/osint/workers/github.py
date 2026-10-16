"""GitHub worker — resolves a query to a GitHub user, then pulls profile + recent repos + language mix."""
from __future__ import annotations

import re

from ...config import load_settings
from ..logging import get_logger
from ..result import WorkerResult
from .base import worker

API = "https://api.github.com"
log = get_logger("github")
_GH_URL = re.compile(r"github\.com/([A-Za-z0-9-]{1,39})", re.I)


def _search_term(query: str) -> str:
    """Normalize @handle / github.com/handle to a clean GitHub search term."""
    q = query.strip()
    m = _GH_URL.search(q)
    if m:
        return m.group(1)
    return q[1:] if q.startswith("@") else q


@worker("github", timeout=15)
async def github_worker(query: str) -> WorkerResult:
    import httpx  # lazy: keeps this module (and _search_term) importable without httpx installed
    settings = load_settings()
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "AIGlass"}
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"

    async with httpx.AsyncClient(timeout=15) as client:
        search = await client.get(
            f"{API}/search/users", params={"q": _search_term(query), "per_page": 1}, headers=headers
        )
        if search.status_code != 200:
            log.warning("search status=%s body=%s", search.status_code, search.text[:200])
            return WorkerResult.failed("github", f"search HTTP {search.status_code}")

        items = search.json().get("items", [])
        if not items:
            return WorkerResult(provider="github", success=True, confidence=0.0, data={})

        username = items[0]["login"]
        profile = await client.get(f"{API}/users/{username}", headers=headers)
        repos = await client.get(
            f"{API}/users/{username}/repos", params={"sort": "updated", "per_page": 5}, headers=headers
        )

    pj = profile.json()
    languages: dict[str, int] = {}
    repo_list: list[dict] = []
    for repo in repos.json():
        lang = repo.get("language")
        if lang:
            languages[lang] = languages.get(lang, 0) + 1
        repo_list.append({
            "name": repo.get("name"),
            "language": lang,
            "stars": repo.get("stargazers_count"),
            "updated": repo.get("updated_at"),
        })

    return WorkerResult(
        provider="github",
        success=True,
        confidence=0.9,
        data={
            "username": pj.get("login"),
            "name": pj.get("name"),
            "company": pj.get("company"),
            "location": pj.get("location"),
            "bio": pj.get("bio"),
            "followers": pj.get("followers"),
            "following": pj.get("following"),
            "public_repos": pj.get("public_repos"),
            "blog": pj.get("blog"),
            "languages": languages,
            "repos": repo_list,
        },
    )
