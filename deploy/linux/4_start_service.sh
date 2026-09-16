#!/usr/bin/env bash
# ==============================================================================
# MaintainWise 2.0 - Start Linux Systemd Background Service
# ==============================================================================
set -e

export LC_ALL=C.UTF-8
export LANG=C.UTF-8

if [ "$(id -u)" -ne 0 ]; then
    echo "Starting maintainwise service with sudo..."
    sudo systemctl start maintainwise
else
    systemctl start maintainwise
fi

echo "✅ maintainwise service started successfully!"
echo ""
echo "Service status:"
systemctl status maintainwise --no-pager || true

echo ""
echo "Access in browser: http://127.0.0.1:8000"
