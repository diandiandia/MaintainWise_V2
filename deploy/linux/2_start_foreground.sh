#!/usr/bin/env bash
# ==============================================================================
# MaintainWise 2.0 - Linux Interactive Foreground Startup (Port 8000)
# ==============================================================================
set -e

export LC_ALL=C.UTF-8
export LANG=C.UTF-8

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
VENV_PYTHON="${BACKEND_DIR}/venv/bin/python"

if [ -x "${VENV_PYTHON}" ]; then
    PYTHON_EXEC="${VENV_PYTHON}"
else
    PYTHON_EXEC="python3"
fi

IP_ADDR=$(hostname -I 2>/dev/null | awk '{print $1}')
IP_ADDR=${IP_ADDR:-"127.0.0.1"}

echo "======================================================================="
echo "       MaintainWise 2.0 - Linux Interactive Foreground Startup"
echo "======================================================================="
echo ""
echo "[*] Starting single-port full-stack service (FastAPI + Vue 3 SPA)..."
echo "[*] Local browser access:    http://127.0.0.1:8000"
echo "[*] Workshop LAN access:     http://${IP_ADDR}:8000"
echo ""
echo "Press Ctrl + C to stop the foreground test server."
echo ""

cd "${BACKEND_DIR}"
PYTHONPATH="${BACKEND_DIR}" exec ${PYTHON_EXEC} -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir "${BACKEND_DIR}"
