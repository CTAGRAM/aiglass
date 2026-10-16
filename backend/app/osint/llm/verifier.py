"""Claim verifier. Falls back to marking claims 'unverified' when no LLM is configured."""
from __future__ import annotations

import json

from . import chat


async def verify(claims: list[str]) -> list[dict]:
    if not claims:
        return []
    out = await chat(
        [
            {"role": "system", "content": "For each claim, judge whether it is internally consistent and "
                                          "plausible. Reply ONLY with a JSON list of "
                                          "{claim, verified(bool), note}."},
            {"role": "user", "content": json.dumps(claims)},
        ],
        max_tokens=400,
    )
    if out and "[" in out and "]" in out:
        try:
            data = json.loads(out[out.index("["): out.rindex("]") + 1])
            if isinstance(data, list):
                return data
        except Exception:  # noqa: BLE001
            pass
    return [{"claim": c, "verified": None, "note": "unverified (no LLM configured)"} for c in claims]
