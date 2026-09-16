#!/usr/bin/env bash
# ==============================================================================
# MaintainWise 2.0 - Linux Background Daemon Restart Script
# ==============================================================================
set -e

SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

bash "${SCRIPT_DIR}/stop_background.sh"
sleep 1
bash "${SCRIPT_DIR}/start_background.sh"
