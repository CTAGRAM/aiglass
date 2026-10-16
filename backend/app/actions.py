"""Extract actionable items from a transcript.

v1 is deliberately simple and dependency-free: rule-based cue matching. It's crude but it makes the whole
capture→act loop real and testable. The clean upgrade is to replace `extract_action_items` with one LLM
call (same return type) — every caller stays the same.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Phrases that signal the speaker intends something to happen.
_CUES = (
    "remind", "remember", "don't forget", "dont forget", "need to", "have to",
    "make sure", "todo", "to-do", "let's", "lets ", "i'll", "i will", "we should",
    "schedule", "book", "buy", "order", "email", "call", "text", "message", "send",
)

# Map a matched cue to a coarse action kind, so the orchestrator can route it.
_KIND_KEYWORDS = {
    "email": ("email", "mail"),
    "call": ("call", "phone", "ring"),
    "message": ("text", "message", "whatsapp", "dm"),
    "buy": ("buy", "order", "purchase"),
    "schedule": ("schedule", "book", "meeting", "appointment", "calendar"),
    "remind": ("remind", "remember", "forget"),
}


@dataclass
class ActionItem:
    text: str
    kind: str  # email | call | message | buy | schedule | remind | todo


def _classify(sentence: str) -> str:
    s = sentence.lower()
    for kind, keywords in _KIND_KEYWORDS.items():
        if any(k in s for k in keywords):
            return kind
    return "todo"


def extract_action_items(transcript: str) -> list[ActionItem]:
    items: list[ActionItem] = []
    seen: set[str] = set()
    for raw in re.split(r"[.!?\n]+", transcript):
        sentence = raw.strip()
        if not sentence:
            continue
        low = sentence.lower()
        if any(cue in low for cue in _CUES):
            key = low
            if key in seen:
                continue
            seen.add(key)
            items.append(ActionItem(text=sentence, kind=_classify(sentence)))
    return items
