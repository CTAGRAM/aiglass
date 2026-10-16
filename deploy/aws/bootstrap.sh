#!/usr/bin/env bash
# Bootstrap the aiGlass backend + Hermes on a fresh Ubuntu 22.04 instance.
# Run on the instance (after SSH). Expects env: REPO_URL, GROQ_API_KEY.
# Untested end-to-end by the author — paste any error back and we'll fix it.
set -euo pipefail

: "${REPO_URL:?set REPO_URL to your aigr git repo}"
: "${LLM_API_KEY:?set LLM_API_KEY (bearer token for your OpenAI-compatible LLM endpoint)}"
LLM_BASE_URL="${LLM_BASE_URL:-https://api.groq.com/openai/v1}"   # your endpoint's /v1 base
LLM_MODEL="${LLM_MODEL:-llama-3.2-11b-vision-preview}"           # a vision-capable model id
# API token: reuse an existing one on redeploys, else generate a fresh one.
API_TOKEN="${API_TOKEN:-$(grep -s '^API_TOKEN=' /etc/aiglass.env | cut -d= -f2)}"
API_TOKEN="${API_TOKEN:-$(openssl rand -hex 24)}"

echo "==> Installing system packages"
sudo apt-get update -y
sudo apt-get install -y python3-venv python3-pip git curl

echo "==> Fetching the repo"
cd "$HOME"
[ -d aigr ] || git clone "$REPO_URL" aigr
cd aigr/backend

echo "==> Python env + deps"
python3 -m venv .venv
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install -r requirements.txt

echo "==> Writing environment (/etc/aiglass.env)"
# STT=mock: Gemini Live handles live audio app-side; the app POSTs turns to /turn as text.
# Vision (and Hermes' brain) use YOUR OpenAI-compatible LLM endpoint.
sudo tee /etc/aiglass.env >/dev/null <<EOF
AIGLASS_DB=$HOME/aiglass.db
API_TOKEN=$API_TOKEN
STT_PROVIDER=mock
VISION_PROVIDER=llm
VISION_BASE_URL=$LLM_BASE_URL
VISION_MODEL=$LLM_MODEL
VISION_API_KEY=$LLM_API_KEY
ORCH_PROVIDER=hermes
HERMES_URL=http://127.0.0.1:8080
AIGLASS_API_URL=http://127.0.0.1:8000
EOF
echo "==> API_TOKEN = $API_TOKEN   (use this as 'Authorization: Bearer <token>' from the app)"

echo "==> systemd service: backend API"
sudo tee /etc/systemd/system/aiglass-backend.service >/dev/null <<EOF
[Unit]
Description=aiGlass backend (FastAPI)
After=network.target
[Service]
EnvironmentFile=/etc/aiglass.env
WorkingDirectory=$HOME/aigr/backend
ExecStart=$HOME/aigr/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
User=$USER
[Install]
WantedBy=multi-user.target
EOF

echo "==> systemd service: MCP server (Hermes seam)"
sudo tee /etc/systemd/system/aiglass-mcp.service >/dev/null <<EOF
[Unit]
Description=aiGlass MCP server
After=network.target
[Service]
EnvironmentFile=/etc/aiglass.env
WorkingDirectory=$HOME/aigr/backend
ExecStart=$HOME/aigr/backend/.venv/bin/python -m app.mcp_server
Restart=always
User=$USER
[Install]
WantedBy=multi-user.target
EOF

echo "==> Installing MCP dep + starting services"
./.venv/bin/pip install "mcp>=1.0" || echo "WARN: mcp install failed; API still runs, MCP seam disabled"
sudo systemctl daemon-reload
sudo systemctl enable --now aiglass-backend.service
sudo systemctl enable --now aiglass-mcp.service || true

echo "==> Backend health:"
sleep 3
curl -s http://127.0.0.1:8000/health || echo "  (not up yet — check: journalctl -u aiglass-backend -n 50)"

cat <<'NOTE'

==> NEXT: install Hermes (the action brain)
    curl -fsSL https://hermes-agent.nousresearch.com/install.sh | sh
    hermes init         # set LLM = your OpenAI-compatible endpoint (same LLM_BASE_URL / LLM_MODEL)
                        # connect the aiglass MCP server so Hermes can read memory + act
    See docs/HERMES_DEPLOY.md. Until Hermes is up, action items queue gracefully (no crash).

Manage:  sudo systemctl status aiglass-backend
Logs:    journalctl -u aiglass-backend -f
NOTE
