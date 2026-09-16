#!/usr/bin/env bash
# ==============================================================================
# MaintainWise 2.0 - Linux Background Daemon Stop Script
# 安全终止后台 MaintainWise 守护进程并清理 PID 锁文件
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

echo "======================================================================="
echo "       MaintainWise 2.0 - 正在停止后台守护服务..."
echo "======================================================================="

STOPPED=false

# 1. 优先通过 PID 文件终止
if [ -f "${PID_FILE}" ]; then
    PID=$(cat "${PID_FILE}" 2>/dev/null || true)
    if [ -n "${PID}" ] && kill -0 "${PID}" 2>/dev/null; then
        echo "[*] 发送终止信号至 PID: ${PID}..."
        kill -15 "${PID}" 2>/dev/null || true
        for i in {1..10}; do
            if ! kill -0 "${PID}" 2>/dev/null; then
                STOPPED=true
                break
            fi
            sleep 0.5
        done
        if ! $STOPPED && kill -0 "${PID}" 2>/dev/null; then
            echo "[*] 进程未退出，强制终止 (SIGKILL)..."
            kill -9 "${PID}" 2>/dev/null || true
            STOPPED=true
        fi
    fi
    rm -f "${PID_FILE}"
fi

# 2. 补充清理可能未记录在 PID 文件的 uvicorn 残留进程
STRAY_PIDS=$(pgrep -f "uvicorn app.main:app" 2>/dev/null || true)
if [ -n "${STRAY_PIDS}" ]; then
    for sp in ${STRAY_PIDS}; do
        echo "[*] 终止 MaintainWise 进程 (PID: ${sp})..."
        kill -15 "${sp}" 2>/dev/null || true
        sleep 0.5
        kill -9 "${sp}" 2>/dev/null || true
        STOPPED=true
    done
fi

if $STOPPED; then
    echo "✅ MaintainWise 2.0 后台服务已成功停止！"
else
    echo "ℹ️  未检测到运行中的 MaintainWise 2.0 后台服务。"
fi
