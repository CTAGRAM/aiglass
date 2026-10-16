#!/usr/bin/env bash
# aiGlass VPS setup — installs the backend as a systemd service on Ubuntu 24.04.
# Run as root on the box:  bash /opt/aiglass/deploy/setup.sh
set -euo pipefail

APP_DIR=/opt/aiglass
BACKEND="$APP_DIR/backend"

echo "==> System packages"
apt-get update -y
apt-get install -y python3 python3-venv python3-pip git ufw curl

echo "==> Firewall (SSH + backend port 8000)"
ufw allow OpenSSH || true
ufw allow 8000/tcp || true
yes | ufw enable || true

echo "==> Python venv + deps"
cd "$BACKEND"
python3 -m venv .venv
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install -r requirements.txt

echo "==> Default .env (edit to go live)"
if [ ! -f "$BACKEND/.env" ]; then
  cat > "$BACKEND/.env" <<ENV
# --- flip these to go live ---
ORCH_PROVIDER=mock          # mock | hermes
HERMES_URL=http://127.0.0.1:8080
HERMES_API_KEY=

VISION_PROVIDER=mock        # mock | llm  (point llm at YOUR endpoint)
VISION_BASE_URL=            # e.g. https://your-llm-host/v1
VISION_API_KEY=
VISION_MODEL=

AIGLASS_DB=$BACKEND/aiglass.db
ENV
fi

echo "==> systemd: aiglass-backend (FastAPI on :8000)"
cat >/etc/systemd/system/aiglass-backend.service <<UNIT
[Unit]
Description=aiGlass backend (FastAPI)
After=network.target
[Service]
WorkingDirectory=$BACKEND
EnvironmentFile=$BACKEND/.env
ExecStart=$BACKEND/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable --now aiglass-backend

echo "==> Done. Check:  curl http://127.0.0.1:8000/health"
echo "Note: the MCP server is NOT a network service — Hermes launches it over stdio."
echo "      See deploy/README.md to install Hermes and wire the MCP seam."
