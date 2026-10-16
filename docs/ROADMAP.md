# Roadmap

> **Pivot → Lane B (buy AR hardware, build the brain).** Target device: **Brilliant Labs Halo** (camera +
> display + speaker + open SDK, ships now; ports to XREAL Aura later). The backend + Hermes brain below is
> unchanged and reused as-is. Phase 3 (DIY firmware) is now **Lane-A-only / optional**; the new last mile
> is the **device app** (see task list). Phases 1–2 are done and verified regardless of hardware.

Locked scope: **sleek DIY AI glasses ("image 2" look)** — XIAO ESP32-S3 Sense (camera + mic) + MAX98357
bone-conduction speaker in a normal-looking frame, self-hosted backend, **Hermes** orchestrator brain.
~₹3,500–5,500 hardware. **No HUD/display** — audio-first: the AI speaks answers and detail goes to the
phone app (like Ray-Ban Meta / Omi). A display can't be sleek at this tier — see [BOM.md](BOM.md).

Each phase has a concrete **verify** gate. We don't move on until it's green.

## Phase 1 — Backend core ✅ (in progress)
Self-hostable FastAPI backend: capture → STT → memory → action items → orchestrator.
Pluggable providers (mock defaults, stdlib-only core).
- **Verify:** `python3 backend/tests/test_pipeline.py` runs the full pipeline with mock STT + mock
  orchestrator and asserts transcript stored, memory created, action extracted, action dispatched.

## Phase 2 — Hermes orchestrator on the VPS
Stand up Hermes, connect it to the backend's MCP server, wire the action-item → Hermes handoff.
- **Verify:** an utterance containing "remind me to email Sam" results in Hermes receiving and acting on a
  structured task (observed in Hermes logs / a message back to you).

## Phase 3 — ESP32-S3 firmware
Arduino/ESP-IDF: PDM mic capture + Opus/PCM stream, periodic JPEG frame, I2S audio OUT to the
bone-conduction speaker, button, LiPo, low-power. No display.
- **Verify:** board streams live audio to the backend and the backend transcribes it; a reply audio clip
  from the backend plays through the speaker.

## Phase 4 — Companion app
Rebranded app: BLE pairing, audio/frame forwarding, live transcript + memory browser + AI chat.
- **Verify:** end-to-end — speak → see live transcript in app → action executed by Hermes → spoken reply
  in your ear + phone notification.

## Phase 5 — Sleek enclosure
Thick-temple 3D-printed frame (or gutted audio-glasses shell) that hides the board + battery + speaker,
camera dot at the hinge — the "image 2" look. Fit, comfort, battery life.
- **Verify:** looks like normal glasses at arm's length; all-day-ish battery.

## Non-goals (v1)
- **No display of any kind** — audio-first. A HUD forces a visible module and can't be sleek at this budget.
- No fully invisible/undetectable form factor (a camera dot is visible, like image 2 itself).
- No on-device inference — all cognition is server-side.
