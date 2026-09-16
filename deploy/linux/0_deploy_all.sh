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
echo "  [1] Start Interactive Foreground Test (Recommended for first run)"
echo "      立即前台交互测试启动 (端口 8000)"
echo "  [2] Install & Start Systemd Background Daemon (Production delivery)"
echo "      安装并启动为 Linux Systemd 系统后台守护服务"
echo "  [3] Exit now (Environment is ready)"
echo "      仅完成环境初始化，稍后自行启动"
echo "-----------------------------------------------------------------------"
read -p "Please select [1-3] (Default: 1): " CHOICE
CHOICE=${CHOICE:-1}

case "$CHOICE" in
    1)
        echo "Starting foreground test service..."
        bash "${SCRIPT_DIR}/2_start_foreground.sh"
        ;;
    2)
        echo "Installing and starting background service..."
        if [ "$(id -u)" -ne 0 ]; then
            sudo bash "${SCRIPT_DIR}/3_install_service.sh"
            sudo bash "${SCRIPT_DIR}/4_start_service.sh"
        else
            bash "${SCRIPT_DIR}/3_install_service.sh"
            bash "${SCRIPT_DIR}/4_start_service.sh"
        fi
        ;;
    3)
        echo "Initialization complete. You can control the system via deploy/linux/ scripts."
        ;;
    *)
        echo "Defaulting to foreground test..."
        bash "${SCRIPT_DIR}/2_start_foreground.sh"
        ;;
esac
