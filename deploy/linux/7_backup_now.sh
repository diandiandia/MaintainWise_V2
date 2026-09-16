#!/usr/bin/env bash
# ==============================================================================
# MaintainWise 2.0 - Trigger System Hot Backup (SQLite 3 WAL + Uploads ZIP)
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

echo "======================================================================="
echo "       MaintainWise 2.0 - Live Hot Backup Execution"
echo "======================================================================="
echo ""
echo "Archiving SQLite 3 WAL database and uploaded media assets..."

cd "${BACKEND_DIR}"
PYTHONPATH="${BACKEND_DIR}" ${PYTHON_EXEC} -c "
from app.services.backup_service import execute_system_backup
res = execute_system_backup()
print(f'✅ Full backup created successfully: {res[\"backup_file\"]}')
print(f'   Physical Path: {res[\"backup_path\"]}')
print(f'   Size: {res[\"size_bytes\"]} bytes')
"

echo ""
echo "Tip: You can add this script to crontab for automated daily backups."
echo "Example (runs daily at 2:00 AM):"
echo "0 2 * * * ${SCRIPT_DIR}/7_backup_now.sh > /dev/null 2>&1"
