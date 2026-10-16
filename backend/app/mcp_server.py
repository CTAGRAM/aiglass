"""MCP server — the seam the orchestrator (Hermes / OpenClaw) plugs into.

Exposes the backend's memory + transcript + action tools over the Model Context Protocol, so the agent
brain can read what you saw/heard and file new tasks WITHOUT any custom glue. Both Hermes and OpenClaw
are MCP clients, so the same server works for either.

Requires: pip install 'mcp<2'   (MCP SDK 1.x — 2.x renamed FastMCP)
Run:      python -m app.mcp_server   (stdio transport)
"""
from __future__ import annotations

import json
import os
import urllib.request

from .config import load_settings
from .face.store import FaceStore
from .memory.store import MemoryStore
from .people import PeopleMemory, default_enricher
from .websearch import public_search

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover - optional dependency
    raise SystemExit("MCP not installed. Run: pip install 'mcp<2'") from exc

settings = load_settings()
memory = MemoryStore(settings.db_path)
people = PeopleMemory(FaceStore(settings.db_path), memory, default_enricher())
mcp = FastMCP("aiglass")

# When Hermes writes a result, best-effort ping the API's /turn so it broadcasts on /ws/events and the
# glasses can speak it immediately. (Multi-process dev seam; production would use a shared Redis channel.)
_API_URL = os.getenv("AIGLASS_API_URL", "http://127.0.0.1:8000")


def _broadcast_result(text: str) -> None:
    try:
        payload = json.dumps({"role": "assistant", "text": text, "source": "hermes"}).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if (tok := os.getenv("API_TOKEN")):
            headers["Authorization"] = f"Bearer {tok}"
        req = urllib.request.Request(
            _API_URL.rstrip("/") + "/turn", data=payload, headers=headers, method="POST",
        )
        urllib.request.urlopen(req, timeout=2.0).close()
    except Exception:
        pass  # never let a broadcast failure break the agent's write


@mcp.tool()
def search_memories(query: str, limit: int = 10) -> list[dict]:
    """Search the user's captured memories by keyword."""
    return [m.__dict__ for m in memory.search_memories(query, limit=limit)]


@mcp.tool()
def recent_transcripts(limit: int = 20) -> list[dict]:
    """Return the most recent conversation transcripts the glasses captured."""
    return [t.__dict__ for t in memory.recent_transcripts(limit=limit)]


@mcp.tool()
def list_action_items(limit: int = 50) -> list[dict]:
    """List open action items extracted from conversations."""
    return [m.__dict__ for m in memory.memories(kind="action_item", limit=limit)]


@mcp.tool()
def add_memory(kind: str, text: str) -> dict:
    """Let the agent write a fact/summary/result back into the user's memory (and sync it live)."""
    mid = memory.add_memory(kind, text, source="orchestrator")
    if kind in ("result", "reply", "answer"):
        _broadcast_result(text)   # surface finished work to the glasses in real time
    return {"id": mid, "kind": kind, "text": text}



@mcp.tool()
async def aiglass_public_search(
    query: str,
    max_results: int = 5,
) -> dict:
    """
    Search the public web.

    Use for:
    - Companies
    - Products
    - Technologies
    - Startups
    """

    return await public_search(
        query=query,
        max_results=max_results,
    )


@mcp.tool()
async def recall_person(name: str) -> dict:
    """
    Recall someone the user has SAVED: who they are, the user's notes about them, recent memories that
    mention them, and a summary of the public profile the user linked for them (if any).

    Only saved people can be recalled; anyone else returns known=false. Never try to find out who a
    stranger is.
    """
    return await people.recall(name)


if __name__ == "__main__":
    mcp.run()
