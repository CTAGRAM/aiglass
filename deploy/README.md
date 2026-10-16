# Deploy to your Vultr VPS

Your box (provisioned via the Vultr API):

| | |
|---|---|
| IP | **65.20.83.134** |
| Region | Mumbai (bom) |
| Spec | Ubuntu 24.04 · 2 GB / 1 vCPU · $10/mo |
| Label | aiglass-hermes |

## 1. Get SSH access
The root password is on the **Vultr dashboard** → your instance → *Overview* (or reset it there).
For key-based login instead, paste me your **public** key (`~/.ssh/id_ed25519.pub`) and I'll add it via the API.

## 2. Copy the code up
```bash
ssh root@65.20.83.134 'mkdir -p /opt/aiglass'
scp -r backend deploy root@65.20.83.134:/opt/aiglass/
```

## 3. Run setup
```bash
ssh root@65.20.83.134 'bash /opt/aiglass/deploy/setup.sh'
curl http://65.20.83.134:8000/health      # -> {"ok": true, ...}
```
The backend now runs as a service (`systemctl status aiglass-backend`) and survives reboots.

## 4. Point vision at your LLM endpoint
Edit `/opt/aiglass/backend/.env`:
```
VISION_PROVIDER=llm
VISION_BASE_URL=https://YOUR-LLM-HOST/v1     # OpenAI-compatible
VISION_API_KEY=YOUR_KEY
VISION_MODEL=YOUR_MODEL
```
`systemctl restart aiglass-backend`.

## 5. Install Hermes + wire the MCP seam
Install Hermes per its official docs ([nousresearch/hermes-agent](https://github.com/nousresearch/hermes-agent)) —
I won't fabricate the exact command; follow their installer. Then:

- Configure Hermes' **LLM** to your custom endpoint (the same `BASE_URL` + key as above).
- Add our **MCP server** to Hermes' MCP config as a stdio server so it can read/write memory:
  ```
  command: /opt/aiglass/backend/.venv/bin/python
  args:    ["-m", "app.mcp_server"]
  cwd:     /opt/aiglass/backend
  ```
- Point the backend at Hermes in `.env`: `ORCH_PROVIDER=hermes`, `HERMES_URL=...`, then
  `systemctl restart aiglass-backend`.

Verify end-to-end with `backend/tests/test_hermes_handoff.py` and a live "remind me to…" utterance.

## ⚠️ Security before real use
Port 8000 is currently open to the internet with **no auth**. Before streaming real data:
- restrict it (`ufw allow from <your-phone-ip> to any port 8000` and remove the open rule), **or**
- put it behind **Caddy/Nginx with TLS + a bearer token**.
Also **rotate the Vultr API key** you shared earlier, and keep `.env` secrets off git (already gitignored).
