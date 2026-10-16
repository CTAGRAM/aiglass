"""Summarize a profile report into 1-2 spoken sentences. Falls back to a deterministic template."""
from __future__ import annotations

from . import chat


def _heuristic(report: dict) -> str:
    p = report.get("person") or {}
    bits: list[str] = []
    if p.get("name"):
        bits.append(p["name"])
    if p.get("company"):
        bits.append(f"at {p['company']}")
    if p.get("bio"):
        bits.append(f"— {p['bio']}")
    return " ".join(bits) or report.get("summary") or "No confident match found."


async def summarize(report: dict) -> str:
    out = await chat(
        [
            {"role": "system", "content": "Summarize this profile report in 1-2 short, natural "
                                          "spoken sentences for someone wearing smart glasses."},
            {"role": "user", "content": str(report)[:4000]},
        ],
        max_tokens=120,
    )
    return out or _heuristic(report)
