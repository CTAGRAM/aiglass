#!/usr/bin/env bash
# Put HTTPS in front of the backend with Caddy + a free Let's Encrypt cert.
# Uses a nip.io hostname derived from the public IP, so no domain purchase is needed.
# Prereq: ports 80 AND 443 open in the Lightsail firewall. Run on the instance.
set -euo pipefail

IP="${IP:-$(curl -s https://api.ipify.org)}"
HOST="${HOST:-$(echo "$IP" | tr '.' '-').nip.io}"     # e.g. 43-205-136-220.nip.io
echo "==> HTTPS host: https://$HOST  ->  127.0.0.1:8000"

echo "==> Installing Caddy"
sudo apt-get install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
  | sudo gpg --batch --yes --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
  | sudo tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null
sudo apt-get update -y && sudo apt-get install -y caddy

echo "==> Configuring reverse proxy (auto-HTTPS)"
sudo tee /etc/caddy/Caddyfile >/dev/null <<EOF
$HOST {
    reverse_proxy 127.0.0.1:8000
}
EOF
sudo systemctl reload caddy 2>/dev/null || sudo systemctl restart caddy

echo ""
echo "==> Done. In ~30s the backend is reachable at:  https://$HOST"
echo "    Caddy is fetching a Let's Encrypt cert (needs ports 80 + 443 open)."
echo "    Point the app's backend URL at  https://$HOST  (no :8000 needed)."
echo "    Optional hardening: once HTTPS works, close public port 8000 so all traffic is encrypted."
