"""Unit tests for the /v1/chat/completions shim helpers (stdlib only).

`python3 backend/tests/test_shim.py`
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.shim import extract_task, shape_completion  # noqa: E402


def test_extract_task_takes_last_user_message():
    msgs = [
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "ok"},
        {"role": "user", "content": "add milk to my shopping list"},
    ]
    assert extract_task(msgs) == "add milk to my shopping list"


def test_extract_task_ignores_assistant_and_empty():
    assert extract_task([{"role": "assistant", "content": "hi"}]) == ""
    assert extract_task([{"role": "user", "content": "  "}]) == ""
    assert extract_task([]) == ""


def test_shape_completion_matches_app_contract():
    out = shape_completion("done, added milk")
    # The app reads choices[0].message.content — that path must exist.
    assert out["choices"][0]["message"]["content"] == "done, added milk"
    assert out["choices"][0]["message"]["role"] == "assistant"
    assert out["object"] == "chat.completion"


def _main():
    tests = [
        test_extract_task_takes_last_user_message,
        test_extract_task_ignores_assistant_and_empty,
        test_shape_completion_matches_app_contract,
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
