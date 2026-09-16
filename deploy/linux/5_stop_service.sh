#!/usr/bin/env bash
# ==============================================================================
# MaintainWise 2.0 - Stop Linux Systemd Background Service
# ==============================================================================
set -e

export LC_ALL=C.UTF-8
export LANG=C.UTF-8

if [ "$(id -u)" -ne 0 ]; then
    echo "Stopping maintainwise service with sudo..."
    sudo systemctl stop maintainwise
else
    systemctl stop maintainwise
fi

echo "✅ maintainwise service has been stopped."
