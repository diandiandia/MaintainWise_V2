#!/usr/bin/env bash
# ==============================================================================
# MaintainWise 2.0 - Linux Unified CLI Control Script
# Usage: ./maintainwise.sh [deploy|start|stop|restart|status|logs|backup|help]
# ==============================================================================
set -e
export LC_ALL=C.UTF-8
export LANG=C.UTF-8

SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ACTION="${1:-}"

print_usage() {
    echo "======================================================================="
    echo "       MaintainWise 2.0 - 智能工厂设备系统总控入口"
    echo "======================================================================="
    echo "用法 (Usage):"
    echo "  $0 <action>  或  ./mw.sh <action>"
    echo ""
    echo "常用指令 (Commands):"
    echo "  deploy   一键全自动依赖安装、数据库初始化与后台守护部署"
    echo "  start    一键后台持久守护启动 (setsid 独立会话，退出终端不中断)"
    echo "  stop     一键安全平滑停止服务并释放端口与锁文件"
    echo "  restart  一键平滑重启后台服务"
    echo "  status   查看后台服务运行状态、PID、CPU/内存占用及监听端口"
    echo "  logs     实时跟踪查看最新运行日志 (tail -f)"
    echo "  backup   立即执行一次 SQLite WAL 全量热备份 (生成 ZIP)"
    echo "  help     查看本帮助信息"
    echo "======================================================================="
}

case "${ACTION}" in
    deploy|install)
        exec bash "${SCRIPT_DIR}/deploy/linux/0_deploy_all.sh"
        ;;
    start)
        exec bash "${SCRIPT_DIR}/deploy/linux/start_background.sh"
        ;;
    stop)
        exec bash "${SCRIPT_DIR}/deploy/linux/stop_background.sh"
        ;;
    restart)
        exec bash "${SCRIPT_DIR}/deploy/linux/restart_background.sh"
        ;;
    status)
        exec bash "${SCRIPT_DIR}/deploy/linux/status.sh"
        ;;
    logs|log)
        LOG_FILE="${SCRIPT_DIR}/logs/maintainwise.log"
        if [ ! -f "${LOG_FILE}" ]; then
            echo "日志文件尚不存在: ${LOG_FILE}"
            exit 1
        fi
        echo "正在实时跟踪日志 (${LOG_FILE})，按 Ctrl+C 退出..."
        exec tail -f -n 50 "${LOG_FILE}"
        ;;
    backup)
        exec bash "${SCRIPT_DIR}/deploy/linux/7_backup_now.sh"
        ;;
    help|-h|--help)
        print_usage
        exit 0
        ;;
    *)
        print_usage
        if [ -n "${ACTION}" ]; then
            echo ""
            echo "❌ 未知参数: '${ACTION}'"
            exit 1
        else
            exit 0
        fi
        ;;
esac
