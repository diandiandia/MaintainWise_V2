#!/usr/bin/env bash
# ==============================================================================
# MaintainWise 2.0 - Linux Background Daemon Startup (nohup & disown)
# 退出 Shell / 断开 SSH 终端后依然在后台稳定持久运行
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

BACKEND_DIR="${ROOT_DIR}/backend"
LOGS_DIR="${ROOT_DIR}/logs"
DATA_DIR="${ROOT_DIR}/data"
PID_FILE="${ROOT_DIR}/maintainwise.pid"
LOG_FILE="${LOGS_DIR}/maintainwise.log"

mkdir -p "${LOGS_DIR}" "${DATA_DIR}/uploads/qrcodes" "${DATA_DIR}/backups"

VENV_PYTHON="${BACKEND_DIR}/venv/bin/python"
if [ -x "${VENV_PYTHON}" ]; then
    PYTHON_EXEC="${VENV_PYTHON}"
else
    PYTHON_EXEC="$(which python3)"
fi

# 检查是否已在运行
if [ -f "${PID_FILE}" ]; then
    OLD_PID=$(cat "${PID_FILE}" 2>/dev/null || true)
    if [ -n "${OLD_PID}" ] && kill -0 "${OLD_PID}" 2>/dev/null; then
        echo "⚠️  MaintainWise 2.0 服务已在后台运行中！(PID: ${OLD_PID})"
        echo "    - 访问地址: http://127.0.0.1:8000"
        echo "    - 查看日志: tail -f ${LOG_FILE}"
        echo "    - 停止服务: ./stop.sh 或 bash ${SCRIPT_DIR}/stop_background.sh"
        exit 0
    else
        rm -f "${PID_FILE}"
    fi
fi

# 检查 8000 端口是否已被其他进程占用
OCCUPIED_PID=$(pgrep -f "uvicorn app.main:app" 2>/dev/null || true)
if [ -n "${OCCUPIED_PID}" ]; then
    echo "⚠️  检测到 MaintainWise 实例已在运行中 (PID: ${OCCUPIED_PID})！"
    echo "    若需重新启动，请先执行 ./stop.sh 关闭后再启动。"
    exit 0
fi

echo "======================================================================="
echo "       MaintainWise 2.0 - 正在启动后台守护服务..."
echo "======================================================================="

# 后台启动 uvicorn 并脱离终端会话 (setsid + /dev/null 输入脱离 + disown)
cd "${BACKEND_DIR}"
PYTHONPATH="${BACKEND_DIR}" setsid "${PYTHON_EXEC}" -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --app-dir "${BACKEND_DIR}" < /dev/null >> "${LOG_FILE}" 2>&1 &

NEW_PID=$!
echo "${NEW_PID}" > "${PID_FILE}"
disown "${NEW_PID}" 2>/dev/null || true

# 留出 2 秒检测进程是否健在
sleep 2

if ! kill -0 "${NEW_PID}" 2>/dev/null; then
    echo "❌ 服务启动失败！进程已意外退出，请查看末尾日志："
    tail -n 20 "${LOG_FILE}"
    rm -f "${PID_FILE}"
    exit 1
fi

IP_ADDR=$(hostname -I 2>/dev/null | awk '{print $1}')
IP_ADDR=${IP_ADDR:-"127.0.0.1"}

echo ""
echo "✅ MaintainWise 2.0 后台守护服务启动成功！"
echo "-----------------------------------------------------------------------"
echo "  [●] 运行状态:     后台持久运行 (已免疫 SIGHUP，退出 Shell/终端不中断)"
echo "  [●] 进程 PID:     ${NEW_PID}"
echo "  [●] 本地访问:     http://127.0.0.1:8000"
echo "  [●] 车间局域网:   http://${IP_ADDR}:8000"
echo "  [●] 运行日志:     ${LOG_FILE}"
echo "-----------------------------------------------------------------------"
echo "常用运维命令："
echo "  - 查看服务状态:   ./status.sh  (或 bash deploy/linux/status.sh)"
echo "  - 停止后台服务:   ./stop.sh    (或 bash deploy/linux/stop_background.sh)"
echo "  - 重启后台服务:   ./restart.sh (或 bash deploy/linux/restart_background.sh)"
echo "  - 实时跟踪日志:   tail -f logs/maintainwise.log"
echo "======================================================================="
