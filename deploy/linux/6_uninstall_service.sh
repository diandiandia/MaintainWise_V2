#!/usr/bin/env bash
# ==============================================================================
# MaintainWise 2.0 - Uninstall Linux Systemd Background Service
# ==============================================================================
set -e

export LC_ALL=C.UTF-8
export LANG=C.UTF-8

if [ "$(id -u)" -ne 0 ]; then
    echo "❌ Error: Root or sudo privilege required. Please run: sudo $0"
    exit 1
fi

SERVICE_FILE="/etc/systemd/system/maintainwise.service"

echo "Stopping and disabling maintainwise service..."
systemctl stop maintainwise 2>/dev/null || true
systemctl disable maintainwise 2>/dev/null || true

if [ -f "${SERVICE_FILE}" ]; then
    rm -f "${SERVICE_FILE}"
    systemctl daemon-reload
    echo "✅ maintainwise service removed successfully."
else
    echo "Service file does not exist. Nothing to remove."
fi
