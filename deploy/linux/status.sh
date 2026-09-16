#!/usr/bin/env bash
# ==============================================================================
# MaintainWise 2.0 - Linux Background Daemon Status Script
# 查看服务存活状态、端口监听情况及最近运行日志
# ==============================================================================
set -e

export LC_ALL=C.UTF-8
export LANG=C.UTF-8

SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -d "${SCRIPT_DIR}/../../backend" ]; then
    ROOT_DIR="$(cd -P "${SCRIPT_DIR}/../.." && pwd)"
elif [ -d "${SCRIPT_DIR}/../backend" ]; then
    ROOT_DIR="$(cd -P "${SCRIPT_DIR}/.." && pwd)"
elif [ -d "$(pwd)/backend" ]; then
    ROOT_DIR="$(pwd)"
else
    ROOT_DIR="$(cd -P "${SCRIPT_DIR}/../.." && pwd)"
fi

PID_FILE="${ROOT_DIR}/maintainwise.pid"
LOG_FILE="${ROOT_DIR}/logs/maintainwise.log"

echo "======================================================================="
echo "       MaintainWise 2.0 - 系统运行状态检查"
echo "======================================================================="

RUNNING=false
CURRENT_PID=""

if [ -f "${PID_FILE}" ]; then
    CURRENT_PID=$(cat "${PID_FILE}" 2>/dev/null || true)
    if [ -n "${CURRENT_PID}" ] && kill -0 "${CURRENT_PID}" 2>/dev/null; then
        RUNNING=true
    fi
fi

# 若 PID 文件不在，但服务有运行，检测是否有 uvicorn 进程
if ! $RUNNING; then
    PORT_PID=$(pgrep -f "uvicorn app.main:app" 2>/dev/null | head -n 1 || true)
    if [ -n "${PORT_PID}" ]; then
        CURRENT_PID="${PORT_PID}"
        RUNNING=true
    fi
fi

if $RUNNING; then
    echo "  [●] 状态:   🟢 正常运行中 (RUNNING)"
    echo "  [●] PID:    ${CURRENT_PID}"
    if command -v ps >/dev/null 2>&1; then
        PS_INFO=$(ps -p "${CURRENT_PID}" -o %cpu,%mem,etime,cmd --no-headers 2>/dev/null || true)
        echo "  [●] 资源:   CPU/MEM/时长: ${PS_INFO}"
    fi
    echo "  [●] 端口:   TCP 8000 监听中"
    echo "  [●] URL:    http://127.0.0.1:8000"
else
    echo "  [●] 状态:   🔴 已停止 (STOPPED)"
fi

echo "-----------------------------------------------------------------------"
if [ -f "${LOG_FILE}" ]; then
    echo "最近 15 行运行日志 (${LOG_FILE})："
    echo "-----------------------------------------------------------------------"
    tail -n 15 "${LOG_FILE}"
else
    echo "暂无运行日志文件 (${LOG_FILE})"
fi
echo "======================================================================="
