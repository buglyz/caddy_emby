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
    echo "??? root ??????"
    exit 1
fi

if [[ ! -f "${PWD}/webui/app.py" ]]; then
    echo "??? webui/app.py???????????"
    exit 1
fi

if [[ ! -f /etc/debian_version ]]; then
    echo "????????? Debian/Ubuntu?"
    exit 1
fi

echo "[1/5] ????..."
apt update
apt install -y caddy python3

echo "[2/5] ?? WebUI..."
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
# ????????????????
# CADDY_EMBY_UI_USERNAME=admin
# CADDY_EMBY_UI_PASSWORD=change-me
# ???????????
# CADDY_EMBY_UI_ACME_EMAIL=you@example.com
# ???????????????????? /emby-ui
# CADDY_EMBY_UI_BASE_PATH=
EOF
fi

echo "[3/5] ?? systemd ??..."
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

echo "[4/5] ????..."
systemctl daemon-reload
systemctl enable --now "${APP_NAME}"

echo "[5/5] ???"
echo "WebUI ??: http://${DEFAULT_HOST}:${DEFAULT_PORT}/"
echo "????: ${DATA_DIR}/webui.env"
echo "????: ${DATA_DIR}/sites.json"
echo "????: systemctl status ${APP_NAME} -l"
