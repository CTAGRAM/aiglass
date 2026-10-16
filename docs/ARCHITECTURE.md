# Architecture

Hardware-agnostic by design: the **glasses are just a sensor + display**. All intelligence lives in a
self-hosted backend you fully control, with an agentic orchestrator (Hermes) as the "action brain."
Swap the DIY glasses for Brilliant Labs Halo / Mentra Live later and **none of the backend changes**.

```
┌─────────────────────────────┐        ┌──────────────────────────────────────────────┐
│  GLASSES (DIY XIAO ESP32-S3) │        │  PHONE APP (companion)                        │
│  • OV2640 camera             │  BLE/  │  • BLE pairing + reconnect                     │
│  • PDM mic                   │  WiFi  │  • buffers audio/frames, forwards to backend   │
│  • bone-conduction speaker   │◀──────▶│  • shows transcript / memory / chat            │
│    (AI voice out, no display)│        │  • plays reply audio in your ear               │
│  • LiPo + button             │        └───────────────────────┬──────────────────────┘
└─────────────────────────────┘                                 │ HTTPS + WebSocket
                                                                 ▼
                        ┌────────────────────────────────────────────────────────────┐
                        │  BACKEND (your Linux VPS)  —  backend/                       │
                        │                                                              │
                        │  main.py      WS ingest (audio/frames) + REST (memory/chat)  │
                        │      │                                                       │
                        │      ▼                                                       │
                        │  pipeline.py  ── STT ──▶ transcript ──▶ action extraction    │
                        │      │            (stt/)        (memory/)      (actions.py)   │
                        │      ▼                                                       │
                        │  memory/store.py   SQLite now / Postgres+pgvector in prod    │
                        │      │                                                       │
                        │      ▼                                                       │
                        │  mcp_server.py   exposes tools over MCP  ◀───────────┐       │
                        └───────────────────────────────────┬──────────────────┼───────┘
                                                             │ MCP             │ MCP
                                                             ▼                 │
                        ┌────────────────────────────────────────────────────────────┐
                        │  ORCHESTRATOR (action brain, sandboxed on the VPS)           │
                        │  Hermes Agent (primary)  ·  OpenClaw (pluggable, same seam)  │
                        │  reads memories/transcript, EXECUTES action items:           │
                        │  send email · run code · book · search · message you back    │
                        └────────────────────────────────────────────────────────────┘
```

## Why this shape

- **The MCP server is the integration seam.** Omi already speaks MCP; so do Hermes and OpenClaw.
  Exposing our memory/transcript/action tools over MCP means the orchestrator plugs in without glue code,
  and we can swap Hermes↔OpenClaw later.
- **Providers are pluggable.** `stt/` and `orchestrator/` each have a `base.py` interface with a `mock`
  implementation (default, stdlib-only — so the pipeline runs and tests anywhere) and a real
  implementation (`whisper.py`, `hermes.py`) behind optional imports. Critical on Python 3.14 where heavy
  ML wheels may not exist yet.
- **Capture ≠ cognition.** The glasses never think. They stream. This keeps the wearable cheap, cool, and
  long-lived on battery, and lets you upgrade the "brain" server-side without touching hardware.

## Data flow (one utterance)

1. Glasses stream Opus/PCM audio (and periodic JPEG frames) → phone → backend WS.
2. `pipeline.process()` runs STT → stores transcript → extracts action items → writes memories.
3. Action items are dispatched to the orchestrator over MCP.
4. Hermes executes each item in its sandbox and reports back; the result is pushed to the app and spoken
   into your ear via the bone-conduction speaker (no display — audio-first).

## Security / privacy posture

- Self-hosted: audio, transcripts, and memories never leave your VPS.
- Orchestrator runs tools in a **sandbox** (Hermes/OpenClaw) to bound blast radius.
- TLS in transit; encrypt the SQLite/Postgres volume at rest.
- A hardware button / mute gates capture (don't record continuously without a kill switch).
