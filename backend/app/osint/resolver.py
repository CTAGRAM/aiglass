"""Entity resolution — merge many `WorkerResult`s into one canonical `Person`.

Consumes the WorkerResult contract (was: raw dicts). Adding a new provider = one `elif`; the resolver
never knows how the worker fetched its data.
"""
from __future__ import annotations

from .entity import Person
from .result import WorkerResult


def resolve(results: list[WorkerResult]) -> Person:
    person = Person()
    for r in results:
        if not isinstance(r, WorkerResult) or not r.success:
            continue
        d = r.data or {}

        if r.provider == "github":
            person.name = d.get("name") or person.name
            person.github = d.get("username") or person.github
            person.company = d.get("company") or person.company
            person.bio = d.get("bio") or person.bio
            person.location = d.get("location") or person.location
            person.website = d.get("blog") or person.website
            if d.get("languages"):
                person.attributes["languages"] = d["languages"]
            if d.get("repos"):
                person.attributes["repos"] = d["repos"]
            for k in ("followers", "public_repos"):
                if d.get(k) is not None:
                    person.attributes[k] = d[k]
            person.evidence.append(r.to_dict())

        elif r.provider == "tavily":
            if not person.bio and d.get("answer"):
                person.bio = d["answer"]
            person.evidence.append(r.to_dict())

        elif r.provider == "company":
            if not person.bio and d.get("extract"):
                person.bio = d["extract"]
            if not person.website and d.get("url"):
                person.website = d["url"]
            person.evidence.append(r.to_dict())

        elif r.provider == "memory":
            if d.get("memories"):
                person.evidence.append(r.to_dict())

    return person
