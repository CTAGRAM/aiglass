# Dual-brain architecture — Gemini Live + Hermes, synced in real time

Two brains, each doing what it's best at, over **one shared history**:

- **Gemini Live** — the *reflex*. Native audio+vision, runs from the Android app, answers out loud in
  ~seconds. Handles the live conversation ("what am I looking at?", "read this to me").
- **Hermes** — the *deep brain*. Self-hosted on your VPS, holds **all chat history**, and executes
  durable multi-step tasks (email, calendar, shopping, research) in a sandbox.

They never diverge because **both read and write the same memory store**, and both observe the same
**live event stream**. This is inspired by VisionClaw ([arXiv 2604.03486](https://arxiv.org/html/2604.03486v2)),
which paired Ray-Ban Meta + Gemini Live + OpenClaw and validated the approach.

```
                 ┌──────────── Android app (Ray-Ban via DAT SDK) ────────────┐
   camera+mic ──▶│  ├─▶ Gemini Live  ── spoken reply in your ear (fast reflex)│
                 │  └─▶ backend WS  ── mirror every turn + frame (durable)    │
                 │  ◀── /ws/events ── live results from Hermes (spoken)       │
                 └──────────────────────────┬────────────────────────────────┘
                                            │ HTTPS/WS
                                            ▼
                    ┌────────────── backend (your VPS) ──────────────┐
                    │  shared MEMORY  (SQLite / pgvector)            │  ← single source of truth
                    │  EventHub  ── /ws/events real-time fan-out     │
                    │  /turn  /ingest  /ingest_frame                │
                    └───────────────┬───────────────────────────────┘
                                    │ MCP (reads history, writes results)
                                    ▼
                    ┌──────────── Hermes (sandboxed) ───────────────┐
                    │  reads all memory, executes tasks, writes back │
                    └────────────────────────────────────────────────┘
```

## How the sync actually works

1. **Live turn.** You speak; the app streams audio+frames to **Gemini Live**, which replies out loud.
   The app also POSTs each turn to **`/turn`** → written to shared memory (`kind="turn"`) → **broadcast**
   on `/ws/events`. Now Hermes' history includes it too.
2. **Capture.** Frames go to `/ingest_frame` → captioned → stored as `observation` memories and broadcast.
   Audio/transcripts go to `/ws/ingest` → action items extracted.
3. **Deep work.** Action items are handed to **Hermes** (via the MCP seam). It reads the *full* shared
   history, does the task in its sandbox, and writes the result back with the `add_memory` tool.
4. **Result syncs back live.** That write best-effort pings `/turn` (`source="hermes"`) → broadcast on
   `/ws/events` → the app **speaks the result in your ear** the moment it's done.

So Gemini gives you the instant answer; Hermes quietly finishes the real work and reports back — and every
turn from either brain lands in the same searchable history.

## Routing rule of thumb

| Utterance | Goes to |
|---|---|
| "What does this label say?" / "translate that" | **Gemini Live** (instant, in-context) |
| "Remind me to email Sam" / "add this to my cart" / "book it" | **Hermes** (durable action) |
| Everything | **shared memory** (so both brains and future queries see it) |

The app can route by intent, or send everything to both — the shared store keeps them consistent either way.

## Endpoints that make it work

- `POST /turn` — record a Gemini turn into shared history + broadcast.
- `WS /ws/events` — subscribe to the live stream (app listens here to speak Hermes results).
- `WS /ws/ingest`, `POST /ingest_frame` — audio + camera capture (already wired to broadcast).
- MCP `add_memory(kind="result", ...)` — Hermes writes a finished result → auto-broadcast.

## Scaling note

The `EventHub` is a single-process asyncio fan-out (great for one VPS). For multi-process (API + separate
MCP/Hermes hosts) or multi-VPS, swap `EventHub.publish` for a **Redis pub/sub** channel — the interface is
identical, nothing else changes. `AIGLASS_API_URL` already lets the MCP process reach the API's `/turn`.

## Configuration

- **Gemini** (app-side, real-time): use `gemini-2.5-flash-native-audio-preview` via the Gemini Live API.
- **Gemini** (backend vision, optional): point `VISION_BASE_URL` at Gemini's OpenAI-compatible endpoint +
  `VISION_MODEL=gemini-2.5-flash`, `VISION_PROVIDER=llm`.
- **Hermes**: `ORCH_PROVIDER=hermes`, `HERMES_URL`, `HERMES_API_KEY` (see [HERMES_DEPLOY.md](HERMES_DEPLOY.md)).
