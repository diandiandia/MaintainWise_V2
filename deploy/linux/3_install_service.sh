#!/usr/bin/env bash
# ==============================================================================
# MaintainWise 2.0 - Install Linux Systemd Background Daemon Service
# ==============================================================================
set -e

export LC_ALL=C.UTF-8
export LANG=C.UTF-8

if [ "$(id -u)" -ne 0 ]; then
    echo "❌ Error: Root or sudo privilege required. Please run: sudo $0"
    exit 1
fi

SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -d "${SCRIPT_DIR}/../../backend" ]; then
    ROOT_DIR="$(cd -P "${SCRIPT_DIR}/../.." && pwd)"
elif [ -d "${SCRIPT_DIR}/../backend" ]; then
    ROOT_DIR="$(cd -P "${SCRIPT_DIR}/.." && pwd)"
elif [ -d "$(pwd)/backend" ]; then
    ROOT_DIR="$(pwd)"
else
    ROOT_DIR="$(cd -P "${SCRIPT_DIR}/../.." && pwd)"
fi

BACKEND_DIR="${ROOT_DIR}/backend"
DATA_DIR="${ROOT_DIR}/data"
VENV_PYTHON="${BACKEND_DIR}/venv/bin/python"

if [ -x "${VENV_PYTHON}" ]; then
    PYTHON_EXEC="${VENV_PYTHON}"
else
    PYTHON_EXEC="$(which python3)"
fi

RUN_USER="${SUDO_USER:-$(id -un)}"
SERVICE_FILE="/etc/systemd/system/maintainwise.service"

# Ensure data directory is owned by RUN_USER (prevent SQLite WAL permission denial)
mkdir -p "${DATA_DIR}/uploads/qrcodes" "${DATA_DIR}/backups"
chown -R "${RUN_USER}:${RUN_USER}" "${DATA_DIR}" 2>/dev/null || true
if [ -d "${BACKEND_DIR}/venv" ]; then
    chown -R "${RUN_USER}:${RUN_USER}" "${BACKEND_DIR}/venv" 2>/dev/null || true
fi

echo "======================================================================="
echo "       MaintainWise 2.0 - Install Systemd Daemon Service"
echo "======================================================================="
echo ""
echo "Service Configuration:"
echo "  - Service Name:      maintainwise"
echo "  - Running User:      ${RUN_USER}"
echo "  - Working Directory: ${ROOT_DIR}"
echo "  - Python Executable: ${PYTHON_EXEC}"
echo ""

cat <<EOF > "${SERVICE_FILE}"
[Unit]
Description=MaintainWise 2.0 Factory Maintenance System
After=network.target

[Service]
Type=simple
User=${RUN_USER}
WorkingDirectory=${ROOT_DIR}
Environment="PYTHONPATH=${BACKEND_DIR}"
ExecStart=${PYTHON_EXEC} -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir ${BACKEND_DIR}
Restart=always
RestartSec=5s
KillMode=process
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

chmod 644 "${SERVICE_FILE}"
systemctl daemon-reload
systemctl enable maintainwise

echo "✅ Systemd service installed and enabled for auto-start on boot!"
echo ""
echo "Service commands:"
echo "  Start:   sudo systemctl start maintainwise   (or ./4_start_service.sh)"
echo "  Status:  sudo systemctl status maintainwise"
echo "  Stop:    sudo systemctl stop maintainwise    (or ./5_stop_service.sh)"
echo "  Restart: sudo systemctl restart maintainwise"
echo "  Logs:    sudo journalctl -u maintainwise -f"
