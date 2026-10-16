# Hermes brain — deploy & connect (Phase 2)

Hermes is the **action brain**: it reads what the glasses captured (via our MCP server) and *executes*
action items in a sandbox on your VPS — send the email, run the code, book the thing — then reports back.
OpenClaw can replace it later behind the same MCP seam.

## Two ways to connect (pick one)

**A. MCP pull (recommended, idiomatic Hermes).** Hermes connects to our `aiglass` MCP server, reads open
action items with `list_action_items`, does them, and writes results back with `add_memory`. Hermes owns
the loop; the backend just exposes tools. Most robust — survives Hermes restarts.

**B. HTTP push (simplest, already tested).** The backend POSTs each action item to Hermes as it happens
(`app/orchestrator/hermes.py` → `POST {HERMES_URL}/tasks`). This is what
`backend/tests/test_hermes_handoff.py` verifies. Use it when Hermes exposes a webhook/task endpoint.

> The exact Hermes intake API depends on your Hermes version. `/tasks` + `{instruction, kind, source}`
> is our assumed contract — adjust `HermesOrchestrator._url`/payload to match, or use mode A.

## Deploy steps

1. **Provision a VPS** — Ubuntu 22.04+, 2 vCPU / 4 GB is plenty. Open only SSH + your backend port (put
   it behind Caddy/Nginx with TLS). Everything below runs here so audio/transcripts never leave your box.

2. **Install Hermes** (self-hosted, per [nousresearch/hermes-agent](https://github.com/nousresearch/hermes-agent)):
   ```bash
   curl -fsSL https://hermes-agent.nousresearch.com/install.sh | sh   # one-line install
   hermes init                                                        # set model + messaging channel
   ```
   Give it an LLM key (Claude/GPT/Groq or a local model) and enable **sandboxed** tool execution.

3. **Run the backend + MCP server** on the same VPS:
   ```bash
   cd backend && python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --host 0.0.0.0 --port 8000 &     # ingest + REST API
   python -m app.mcp_server &                            # MCP tools for Hermes
   ```

4. **Connect Hermes to our tools (mode A).** Add the `aiglass` MCP server to Hermes' MCP config so it can
   call `search_memories`, `recent_transcripts`, `list_action_items`, `add_memory`. Hermes now sees
   everything the glasses captured and can write results back into your memory.

5. **Or enable push (mode B).** Point the backend at Hermes and restart uvicorn:
   ```bash
   export ORCH_PROVIDER=hermes
   export HERMES_URL=http://127.0.0.1:8080     # your Hermes task intake
   export HERMES_API_KEY=...                    # if Hermes requires auth
   ```

## Verify

- **Contract:** `python3 backend/tests/test_hermes_handoff.py` → 2/2 (proves the handoff + graceful
  degradation, no real Hermes needed).
- **Live:** speak/type "remind me to email Sam the report" → confirm Hermes receives a structured `email`
  task and messages you back on your chosen channel.

## Security

- Keep tool execution **sandboxed** (Hermes/OpenClaw setting) to bound blast radius.
- TLS on the backend; encrypt the DB volume at rest.
- Store `HERMES_API_KEY` / LLM keys in a `.env` (gitignored), never in code.
- The capture button on the glasses is the kill switch — don't run always-on without it.
