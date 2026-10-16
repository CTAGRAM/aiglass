# aiGlass

A self-hosted AI agent for **Ray-Ban Meta (Gen 1)** glasses. You talk to your glasses; the agent sees
what you see, remembers things for you, and takes real actions — for example, look at a shop's UPI QR,
say the amount, and it prepares the payment for you to approve.

Built July–August 2026; consolidated into this repo in October 2026.

```
Ray-Ban Meta (camera + mic)
        │  Meta Wearables Device Access Toolkit (BLE / Wi-Fi Direct)
        ▼
Android app (Kotlin, android/) ──audio + ~1 fps frames──▶ Gemini Live (real-time voice + vision)
        │   tools: execute · scan_payment_qr · initiate_payment
        ▼
FastAPI backend (backend/)  POST /v1/chat/completions   — AWS Lightsail, Caddy TLS, bearer-token auth
        │  runs each task through the Hermes agent
        ▼
Hermes agent ──▶ Claude Sonnet 4.6
        │  MCP tools (backend/app/mcp_server.py)
        ├── memory: search_memories · recent_transcripts · list_action_items · add_memory
        └── aiglass_public_search (Tavily web search)
```

## What's in the repo

| Path | What |
|---|---|
| `android/` | The glasses app. Based on Intent-Lab's [VisionClaw](https://github.com/Intent-Lab/VisionClaw) Android sample (built on Meta's DAT sample); my additions are listed below. |
| `backend/` | FastAPI backend: OpenAI-compatible `/v1/chat/completions` shim → Hermes agent, MCP server, SQLite memory, pluggable STT (faster-whisper) and vision captioning, live event stream (`/ws/events`). |
| `spidersense/` | ESP32 + 4× VL53L1X haptic band that warns about things approaching from the sides and behind — where the glasses camera can't see. Alerts on time-to-collision, not distance. |
| `deploy/` | AWS Lightsail bootstrap, Caddy + Let's Encrypt TLS, systemd setup. |
| `docs/` | [System overview](docs/SYSTEM_OVERVIEW.md) · [Architecture](docs/ARCHITECTURE.md) · [Dual brain sync](docs/DUAL_BRAIN.md) · [Hermes deploy](docs/HERMES_DEPLOY.md) · [Roadmap](docs/ROADMAP.md) |

## My additions to the Android app

- **UPI QR pay** (`openclaw/PaymentBridge.kt`): ML Kit decodes the QR in the current glasses frame →
  the payee name is read back → the user confirms amount and payee out loud → a `upi://pay` intent opens
  the UPI app. Spoken amounts are capped at ₹1,400, and the user always authorises inside the UPI app.
- **Latest-frame buffer** (`gemini/LatestFrame.kt`): on-demand tools can use exactly what the glasses see now.
- **Gen 1 audio routing** (`gemini/AudioManager.kt`): AI voice plays through the glasses; voice capture
  falls back to the phone mic when the glasses mic is unavailable (see below).
- **Tool routing prompt** (`settings/SettingsManager.kt`): personal tasks and lists are routed to the
  aiglass memory tools, plus a strict confirm-before-pay protocol.

## Hard problems solved

- **Glasses camera stuck on "loading".** Not Wi-Fi: logcat showed `FAILED_TO_BIND_TO_MWA_ACDC_SERVICE`.
  The DAT `APPLICATION_ID=0` placeholder is only honoured when the glasses are in Developer Mode.
- **Gen 1 can't use its mic while the camera streams.** A2DP output to the glasses keeps working, but the
  SCO mic link drops. So the AI speaks through the glasses and the phone mic captures your voice.
- **Personal UPI QRs always declined** — identically in GPay, PhonePe and Paytm. Traced to the shared NPCI
  library: third-party-initiated person-to-person intents are refused; merchant QRs are the right target.
  Also: the payee name inside a QR is set by whoever printed it, so only the bank-resolved name is trustworthy.
- **Agent tool routing.** The agent's built-in empty `todo` tool was catching personal queries before the
  memory tools; fixed with prompt-level routing.

## Run it

**Backend**
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt pytest "mcp<2"
python -m pytest tests/ -q                     # pipeline, shim, events, vision, Hermes hand-off
uvicorn app.main:app --host 0.0.0.0 --port 8000
python -m app.mcp_server                       # MCP tools for the agent (stdio)
```

**Android app**
1. Copy `android/app/src/main/java/.../cameraaccess/Secrets.kt.example` to `Secrets.kt` and fill in your
   Gemini key, backend URL and backend token.
2. Put a GitHub token with `read:packages` in `android/local.properties` as `github_token=...`
   (Meta's DAT SDK is served from GitHub Packages), or export `GITHUB_TOKEN`.
3. Build with Android Studio or `./gradlew :app:installDebug`.

`Secrets.kt` and `local.properties` are gitignored — keys never leave your machine.

## Credits and licences

- Android app based on [Intent-Lab/VisionClaw](https://github.com/Intent-Lab/VisionClaw), which builds on
  Meta's Wearables Device Access Toolkit sample. Use of the toolkit is subject to the
  [Meta Wearables Developer Terms](https://wearables.developer.meta.com/terms) — see `android/LICENSE`
  and `android/NOTICE`.
- Agent: [Nous Research Hermes Agent](https://github.com/nousresearch/hermes-agent).
