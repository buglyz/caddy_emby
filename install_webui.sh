#!/bin/bash
set -euo pipefail

APP_NAME="caddy-emby-ui"
APP_DIR="/opt/${APP_NAME}"
DATA_DIR="/etc/${APP_NAME}"
SERVICE_FILE="/etc/systemd/system/${APP_NAME}.service"
BIN_FILE="${APP_DIR}/app.py"
DEFAULT_PORT="${CADDY_EMBY_UI_PORT:-9780}"
DEFAULT_HOST="${CADDY_EMBY_UI_HOST:-0.0.0.0}"

if [[ $EUID -ne 0 ]]; then
    echo "Please run this script as root."
    exit 1
fi

if [[ ! -f "${PWD}/webui/app.py" ]]; then
    echo "webui/app.py was not found. Run this script from the repository root."
    exit 1
fi

if [[ ! -f /etc/debian_version ]]; then
    echo "This installer currently supports Debian and Ubuntu only."
    exit 1
fi

echo "[1/5] Installing dependencies..."
apt update
apt install -y caddy python3

echo "[2/5] Deploying WebUI..."
mkdir -p "${APP_DIR}" "${DATA_DIR}"
install -m 0755 "${PWD}/webui/app.py" "${BIN_FILE}"

if [[ ! -f "${DATA_DIR}/sites.json" ]]; then
    cat > "${DATA_DIR}/sites.json" <<'JSON'
{
  "sites": []
}
JSON
fi

if [[ ! -f "${DATA_DIR}/webui.env" ]]; then
    cat > "${DATA_DIR}/webui.env" <<EOF
CADDY_EMBY_UI_HOST=${DEFAULT_HOST}
CADDY_EMBY_UI_PORT=${DEFAULT_PORT}
CADDY_EMBY_UI_DATA_DIR=${DATA_DIR}
CADDY_EMBY_UI_CADDYFILE=/etc/caddy/Caddyfile
# Strongly recommended: protect the WebUI with basic auth
# CADDY_EMBY_UI_USERNAME=admin
# CADDY_EMBY_UI_PASSWORD=change-me
# Optional: default ACME email for automatic certificates
# CADDY_EMBY_UI_ACME_EMAIL=you@example.com
# Optional: mount the UI under a base path such as /emby-ui
# CADDY_EMBY_UI_BASE_PATH=
EOF
fi

echo "[3/5] Writing systemd service..."
cat > "${SERVICE_FILE}" <<EOF
[Unit]
Description=Caddy Emby WebUI
After=network.target caddy.service
Wants=network.target caddy.service

[Service]
Type=simple
EnvironmentFile=-${DATA_DIR}/webui.env
ExecStart=/usr/bin/python3 ${BIN_FILE}
WorkingDirectory=${APP_DIR}
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF

echo "[4/5] Enabling service..."
systemctl daemon-reload
systemctl enable --now "${APP_NAME}"

echo "[5/5] Done."
echo "WebUI address: http://${DEFAULT_HOST}:${DEFAULT_PORT}/"
echo "Environment file: ${DATA_DIR}/webui.env"
echo "Site data: ${DATA_DIR}/sites.json"
echo "Check status: systemctl status ${APP_NAME} -l"
