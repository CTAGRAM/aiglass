"""LLM helpers (planner / summarizer / verifier). Every one degrades gracefully to a deterministic
fallback when no LLM endpoint is configured, so the engine never hard-depends on an LLM.

Uses the app's existing OpenAI-compatible endpoint (vision_base_url/vision_api_key/vision_model).
"""
from __future__ import annotations

from ...config import load_settings
from ..logging import get_logger

log = get_logger("llm")


async def chat(messages: list[dict], max_tokens: int = 300, temperature: float = 0.2) -> str | None:
    """Call the configured OpenAI-compatible chat endpoint. Returns None if unconfigured or on error."""
    s = load_settings()
    if not s.vision_api_key:
        return None
    try:
        import httpx
    except Exception:  # pragma: no cover
        return None
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                s.vision_base_url.rstrip("/") + "/chat/completions",
                headers={"Authorization": f"Bearer {s.vision_api_key}", "Content-Type": "application/json"},
                json={"model": s.vision_model, "messages": messages,
                      "max_tokens": max_tokens, "temperature": temperature},
            )
            r.raise_for_status()
            return (r.json()["choices"][0]["message"]["content"] or "").strip()
    except Exception as exc:  # noqa: BLE001
        log.warning("llm chat failed: %s", exc)
        return None
