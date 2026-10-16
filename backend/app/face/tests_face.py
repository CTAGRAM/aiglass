"""Enrolled-only face recognition tests (MockEmbedder — deterministic, dep-free).
    python3 app/face/tests_face.py       # from backend/
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))  # -> backend/

from app.face.embedder import MockEmbedder     # noqa: E402
from app.face.service import FaceService        # noqa: E402
from app.face.store import FaceStore            # noqa: E402


def _svc():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return FaceService(MockEmbedder(), FaceStore(path)), path


def test_enroll_and_recognize_same_face():
    svc, path = _svc()
    try:
        r = svc.enroll(b"alice-face-bytes", "Alice", notes="colleague", lookup_query="rauchg")
        assert r["ok"] and r["name"] == "Alice"
        rec = svc.recognize(b"alice-face-bytes")
        assert rec["recognized"] and rec["name"] == "Alice"
        assert rec["notes"] == "colleague" and rec["lookup_query"] == "rauchg"
        assert rec["score"] >= 0.99
    finally:
        os.remove(path)


def test_unknown_face_returns_unrecognized():
    svc, path = _svc()
    try:
        svc.enroll(b"alice-face-bytes", "Alice")
        rec = svc.recognize(b"a-totally-different-persons-face")
        assert rec["recognized"] is False          # never guesses on a stranger
    finally:
        os.remove(path)


def test_no_face_detected():
    svc, path = _svc()
    try:
        assert svc.enroll(b"", "X")["ok"] is False
        assert svc.recognize(b"")["recognized"] is False
    finally:
        os.remove(path)


def test_list_and_delete():
    svc, path = _svc()
    try:
        svc.enroll(b"a", "Alice")
        svc.enroll(b"b", "Bob")
        assert svc.list() == ["Alice", "Bob"]
        assert svc.delete("Alice") == 1
        assert svc.list() == ["Bob"]
    finally:
        os.remove(path)


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
