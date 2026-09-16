#!/usr/bin/env bash
# ==============================================================================
# MaintainWise 2.0 - Linux Full Automated Deployment Wizard
# ==============================================================================
set -e

export LC_ALL=C.UTF-8
export LANG=C.UTF-8

SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "======================================================================="
echo "       MaintainWise 2.0 - Linux Full Automated Deployment"
echo "======================================================================="
echo ""

# Step 1: Initialize Environment & Database
bash "${SCRIPT_DIR}/1_init_env.sh"

echo ""
echo "-----------------------------------------------------------------------"
echo "Select startup mode / 请选择后续启动方式："
echo "  [1] Start Background Daemon Service (Default & Recommended)"
echo "      一键后台守护启动 (退出 Shell / SSH 不中断，自动生成日志与 PID)"
echo "  [2] Start Interactive Foreground Test"
echo "      前台交互调试启动 (端口 8000，按 Ctrl+C 退出)"
echo "  [3] Install & Start Systemd Daemon (For systemd-enabled hosts)"
echo "      安装并启动为 Linux Systemd 系统后台守护服务"
echo "  [4] Exit now (Environment is ready)"
echo "      仅完成环境初始化，稍后通过 ./start.sh 自行启动"
echo "-----------------------------------------------------------------------"
read -p "Please select [1-4] (Default: 1): " CHOICE
CHOICE=${CHOICE:-1}

case "$CHOICE" in
    1)
        echo "Starting background daemon service..."
        bash "${SCRIPT_DIR}/start_background.sh"
        ;;
    2)
        echo "Starting foreground test service..."
        bash "${SCRIPT_DIR}/2_start_foreground.sh"
        ;;
    3)
        echo "Installing and starting background service..."
        if [ "$(id -u)" -ne 0 ]; then
            sudo bash "${SCRIPT_DIR}/3_install_service.sh"
            sudo bash "${SCRIPT_DIR}/4_start_service.sh"
        else
            bash "${SCRIPT_DIR}/3_install_service.sh"
            bash "${SCRIPT_DIR}/4_start_service.sh"
        fi
        ;;
    4)
        echo "Initialization complete. You can start anytime via ./start.sh or deploy/linux/ scripts."
        ;;
    *)
        echo "Defaulting to background daemon..."
        bash "${SCRIPT_DIR}/start_background.sh"
        ;;
esac
