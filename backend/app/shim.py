"""Helpers for the OpenClaw-compatible /v1/chat/completions shim.

The glasses app (VisionClaw) lets Gemini call one `execute` tool, which POSTs the task to a gateway at
`/v1/chat/completions` (OpenAI shape) and reads back `choices[0].message.content`. Our backend answers
that shape and runs the task through Hermes. Stdlib only, so it's unit-testable without FastAPI.
"""
from __future__ import annotations


def extract_task(messages: list[dict]) -> str:
    """The task = the most recent user message's content."""
    for m in reversed(messages):
        if m.get("role") == "user" and m.get("content"):
            return str(m["content"]).strip()
    return ""


def shape_completion(content: str) -> dict:
    """Wrap a plain result string in the OpenAI chat-completions shape the app parses."""
    return {
        "id": "chatcmpl-aiglass",
        "object": "chat.completion",
        "model": "aiglass-hermes",
        "choices": [
            {"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}
        ],
    }
