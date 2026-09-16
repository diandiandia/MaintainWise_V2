#!/usr/bin/env bash
# MaintainWise 2.0 - 一键查看服务运行状态与日志
SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "${SCRIPT_DIR}/deploy/linux/status.sh"
