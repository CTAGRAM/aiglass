"""People memory: recall works for SAVED people only, and enrichment uses only the link the user saved.

`python3 -m pytest backend/tests/test_people.py`
"""
import asyncio
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.face.embedder import MockEmbedder  # noqa: E402
from app.face.service import FaceService    # noqa: E402
from app.face.store import FaceStore        # noqa: E402
from app.memory.store import MemoryStore    # noqa: E402
from app.people import PeopleMemory         # noqa: E402


class FakeEnricher:
    def __init__(self, fail: bool = False) -> None:
        self.calls: list[str] = []
        self.fail = fail

    async def __call__(self, link: str) -> dict:
        self.calls.append(link)
        if self.fail:
            raise RuntimeError("source down")
        return {"summary": f"profile for {link}"}


def _setup(enricher=None):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    store = FaceStore(path)
    faces = FaceService(MockEmbedder(), store)
    memory = MemoryStore(path)
    return faces, memory, PeopleMemory(store, memory, enricher), path


def test_unsaved_person_is_never_looked_up():
    enrich = FakeEnricher()
    _, _, people, path = _setup(enrich)
    try:
        out = asyncio.run(people.recall("Some Stranger"))
        assert out["known"] is False
        assert enrich.calls == []          # nothing is searched for someone who isn't saved
    finally:
        os.remove(path)


def test_saved_person_recalls_notes_and_memories_without_link():
    enrich = FakeEnricher()
    faces, memory, people, path = _setup(enrich)
    try:
        faces.enroll(b"priya-face", "Priya", notes="met at the Pune AI meetup")
        memory.add_memory("result", "Priya said she is hiring Android devs", source="hermes")
        memory.add_memory("result", "Unrelated note about groceries", source="hermes")
        out = asyncio.run(people.recall("priya"))   # case-insensitive
        assert out["known"] and out["name"] == "Priya"
        assert out["notes"] == "met at the Pune AI meetup"
        assert out["recent"] == ["Priya said she is hiring Android devs"]
        assert out["public_profile"] is None
        assert enrich.calls == []          # no saved link -> no enrichment
    finally:
        os.remove(path)


def test_enrichment_uses_only_the_saved_link():
    enrich = FakeEnricher()
    faces, _, people, path = _setup(enrich)
    try:
        faces.enroll(b"arjun-face", "Arjun", lookup_query="github.com/arjun-dev")
        out = asyncio.run(people.recall("Arjun"))
        assert enrich.calls == ["github.com/arjun-dev"]   # the link, never the bare name
        assert out["public_profile"] == {"summary": "profile for github.com/arjun-dev"}
    finally:
        os.remove(path)


def test_failing_enrichment_never_breaks_recall():
    faces, _, people, path = _setup(FakeEnricher(fail=True))
    try:
        faces.enroll(b"meera-face", "Meera", notes="teammate", lookup_query="github.com/meera")
        out = asyncio.run(people.recall("Meera"))
        assert out["known"] and out["notes"] == "teammate" and out["public_profile"] is None
    finally:
        os.remove(path)


def test_find_merges_several_photos_of_one_person():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        store = FaceStore(path)
        store.enroll("Kabir", [1.0, 0.0], notes="college friend", lookup_query="")
        store.enroll("Kabir", [0.0, 1.0], notes="", lookup_query="linkedin.com/in/kabir")
        rec = store.find("KABIR")
        assert rec["name"] == "Kabir"
        assert rec["notes"] == "college friend"
        assert rec["lookup_query"] == "linkedin.com/in/kabir"
        assert store.find("Nobody") is None
    finally:
        os.remove(path)
