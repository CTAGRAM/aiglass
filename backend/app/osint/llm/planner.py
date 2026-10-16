"""LLM-based worker planning (the "later" upgrade over heuristics). Falls back to the heuristic planner."""
from __future__ import annotations

import json

from ..planner import plan as heuristic_plan
from . import chat


async def plan_llm(query: str, available: list[str]) -> list[str]:
    out = await chat(
        [
            {"role": "system", "content": "You choose which OSINT data sources to query for a lookup. "
                                          "Reply ONLY with a JSON array of source names chosen from the "
                                          "provided list."},
            {"role": "user", "content": f"Query: {query}\nAvailable sources: {available}"},
        ],
        max_tokens=60,
    )
    if out and "[" in out and "]" in out:
        try:
            picked = json.loads(out[out.index("["): out.rindex("]") + 1])
            chosen = [w for w in picked if w in available]
            if chosen:
                return chosen
        except Exception:  # noqa: BLE001
            pass
    heuristic = heuristic_plan(query)
    return [w for w in heuristic if w in available] or heuristic
