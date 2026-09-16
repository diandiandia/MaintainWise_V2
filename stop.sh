#!/usr/bin/env bash
# MaintainWise 2.0 - 一键停止后台服务
SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "${SCRIPT_DIR}/deploy/linux/stop_background.sh"
