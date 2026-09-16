#!/usr/bin/env bash
# MaintainWise 2.0 - 一键后台启动服务 (脱离终端会话持久运行)
SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "${SCRIPT_DIR}/deploy/linux/start_background.sh"
