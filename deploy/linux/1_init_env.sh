#!/usr/bin/env bash
# ==============================================================================
# MaintainWise 2.0 - Linux Environment Automated Initialization
# Supported OS: Ubuntu 20.04/22.04/24.04, Debian 11/12, CentOS/RHEL 8/9, Rocky
# ==============================================================================
set -e

export LC_ALL=C.UTF-8
export LANG=C.UTF-8

# 1. Canonical Physical Path Resolution (cd -P)
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
DATA_DIR="${ROOT_DIR}/data"
VENV_DIR="${BACKEND_DIR}/venv"

echo "======================================================================="
echo "   MaintainWise 2.0 - Linux Environment Automated Initialization"
echo "======================================================================="
echo "[*] Project Root Directory: ${ROOT_DIR}"
echo ""

# 2. Determine privilege (root or sudo)
SUDO=""
if [ "$(id -u)" -ne 0 ]; then
    if command -v sudo &> /dev/null; then
        SUDO="sudo"
    fi
fi

# 3. [STEP 1/4] Automatically install ALL OS-level packages in ONE SHOT
echo "[1/4] Automatically installing OS dependencies (Python3, pip, venv, sqlite3)..."
if command -v apt-get &> /dev/null; then
    # Debian / Ubuntu (Automatically installs python3-venv and python3-pip upfront!)
    echo "  -> Detected apt package manager (Ubuntu/Debian)"
    export DEBIAN_FRONTEND=noninteractive
    ${SUDO} apt-get update -qq -y || true
    ${SUDO} apt-get install -qq -y python3 python3-pip python3-venv python3-full sqlite3 curl || true
elif command -v dnf &> /dev/null; then
    # Fedora / CentOS 8+ / RHEL 8+ / Rocky
    echo "  -> Detected dnf package manager (CentOS/RHEL/Rocky)"
    ${SUDO} dnf install -y python3 python3-pip sqlite curl || true
elif command -v yum &> /dev/null; then
    # CentOS 7 / RHEL 7
    echo "  -> Detected yum package manager"
    ${SUDO} yum install -y python3 python3-pip sqlite curl || true
elif command -v pacman &> /dev/null; then
    # Arch Linux
    echo "  -> Detected pacman package manager"
    ${SUDO} pacman -Sy --noconfirm python python-pip sqlite curl || true
elif command -v apk &> /dev/null; then
    # Alpine Linux
    echo "  -> Detected apk package manager"
    ${SUDO} apk add --no-cache python3 py3-pip sqlite curl || true
fi

if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 runtime not available after installation attempt."
    exit 1
fi
echo "  [OK] Python 3 runtime verified: $(python3 --version)"

# 4. [STEP 2/4] Configure Python Virtual Environment (venv) with Portability Auto-Healing
echo ""
echo "[2/4] Configuring isolated Python virtual environment (backend/venv)..."

# Thorough validation of existing virtual environment:
# A copied or synced venv from another machine/path (e.g. /root -> /home/ubuntu)
# will have hardcoded foreign shebangs or broken symlinks.
VENV_IS_VALID=0
if [ -d "${VENV_DIR}" ]; then
    if [ -x "${VENV_DIR}/bin/python" ]; then
        # Test 1: Python binary executes without error
        if "${VENV_DIR}/bin/python" -c "import sys; exit(0)" 2>/dev/null; then
            # Test 2: Pip module can be loaded via python -m pip
            if "${VENV_DIR}/bin/python" -m pip --version 2>/dev/null | grep -q "pip "; then
                # Test 3: If bin/pip exists, check that its shebang matches current directory
                if [ -f "${VENV_DIR}/bin/pip" ]; then
                    PIP_SHEBANG=$(head -n 1 "${VENV_DIR}/bin/pip" 2>/dev/null || true)
                    if [[ "${PIP_SHEBANG}" == *"${VENV_DIR}"* ]]; then
                        VENV_IS_VALID=1
                    fi
                else
                    VENV_IS_VALID=1
                fi
            fi
        fi
    fi
    
    if [ "$VENV_IS_VALID" -eq 0 ]; then
        echo "  [AUTO-HEAL] Detected foreign, broken, or relocated venv (e.g. copied from another OS/path)."
        echo "  -> Purging foreign venv to rebuild native environment on this host..."
        rm -rf "${VENV_DIR}"
    fi
fi

# Build native venv
if [ ! -d "${VENV_DIR}" ]; then
    echo "  -> Creating native virtual environment: ${VENV_DIR}..."
    if python3 -m venv "${VENV_DIR}" 2>/dev/null; then
        echo "  [OK] Virtual environment created successfully."
    else
        echo "  -> Fallback: Creating pure venv and injecting pip..."
        python3 -m venv --without-pip "${VENV_DIR}" 2>/dev/null || true
    fi
fi

# Determine Python & Pip execution commands (Using python -m pip to eliminate shebang errors)
if [ -x "${VENV_DIR}/bin/python" ]; then
    PYTHON_EXEC="${VENV_DIR}/bin/python"
    # Ensure pip module is available inside venv
    if ! "${PYTHON_EXEC}" -m pip --version &>/dev/null; then
        echo "  -> Installing pip inside virtual environment..."
        GET_PIP_TMP="/tmp/mw_get_pip_$$.py"
        python3 -c "
import urllib.request
for u in ['https://mirrors.aliyun.com/pypi/get-pip.py', 'https://bootstrap.pypa.io/get-pip.py']:
    try:
        req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as r, open('${GET_PIP_TMP}', 'wb') as f:
            f.write(r.read())
        break
    except Exception:
        continue
" 2>/dev/null || curl -fsSL https://bootstrap.pypa.io/get-pip.py -o "${GET_PIP_TMP}" 2>/dev/null || true

        if [ -f "${GET_PIP_TMP}" ]; then
            "${PYTHON_EXEC}" "${GET_PIP_TMP}" -i https://pypi.tuna.tsinghua.edu.cn/simple --no-warn-script-location 2>/dev/null || \
            "${PYTHON_EXEC}" "${GET_PIP_TMP}" --no-warn-script-location 2>/dev/null || true
            rm -f "${GET_PIP_TMP}"
        fi
    fi
    PIP_EXEC="${PYTHON_EXEC} -m pip"
    PIP_FLAGS=""
    echo "  [OK] Using native Python virtual environment: ${PYTHON_EXEC}"
else
    echo "  [WARN] Falling back to global system Python runtime"
    PYTHON_EXEC="python3"
    PIP_EXEC="python3 -m pip"
    PIP_FLAGS="--break-system-packages"
    echo "  [OK] Using system Python: $(which python3)"
fi

# 5. [STEP 3/4] Ensure requirements.txt and install Python dependencies
echo ""
echo "[3/4] Installing Python application dependencies..."
mkdir -p "${BACKEND_DIR}"
if [ ! -f "${BACKEND_DIR}/requirements.txt" ]; then
    echo "  -> Generating default backend/requirements.txt automatically..."
    cat << 'EOF' > "${BACKEND_DIR}/requirements.txt"
fastapi>=0.100.0
uvicorn>=0.23.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
pyjwt>=2.8.0
bcrypt>=4.0.0
python-multipart>=0.0.6
aiofiles>=23.0.0
qrcode>=7.4.2
pillow>=10.0.0
pytest>=7.0.0
httpx>=0.24.0
EOF
fi

# Install dependencies using python -m pip with Tsinghua mirror and official fallback
${PIP_EXEC} install --upgrade pip ${PIP_FLAGS} -i https://pypi.tuna.tsinghua.edu.cn/simple 2>/dev/null || true
${PIP_EXEC} install -r "${BACKEND_DIR}/requirements.txt" ${PIP_FLAGS} -i https://pypi.tuna.tsinghua.edu.cn/simple || \
${PIP_EXEC} install -r "${BACKEND_DIR}/requirements.txt" ${PIP_FLAGS} -i https://pypi.org/simple || \
${PIP_EXEC} install -r "${BACKEND_DIR}/requirements.txt" --break-system-packages --user

echo "  -> Validating backend core modules..."
${PYTHON_EXEC} -c "import fastapi, uvicorn, pydantic, bcrypt, jwt, qrcode, PIL; print('  [OK] Core modules validated successfully.')"

# 6. [STEP 4/4] Initialize SQLite 3 WAL Database & Demo Data
echo ""
echo "[4/4] Initializing SQLite 3 WAL database & seed data..."
mkdir -p "${DATA_DIR}/uploads/qrcodes" "${DATA_DIR}/backups"
cd "${BACKEND_DIR}"
PYTHONPATH="${BACKEND_DIR}" ${PYTHON_EXEC} -c "
from app.db.init_db import init_db
init_db()
print('  [OK] Database tables created and seed data populated.')
"

# Set permissions for non-root user when run with sudo
if [ "$(id -u)" -eq 0 ] && [ -n "${SUDO_USER}" ]; then
    chown -R "${SUDO_USER}:${SUDO_USER}" "${DATA_DIR}" 2>/dev/null || true
    if [ -d "${VENV_DIR}" ]; then
        chown -R "${SUDO_USER}:${SUDO_USER}" "${VENV_DIR}" 2>/dev/null || true
    fi
fi

echo ""
echo "======================================================================="
echo " MaintainWise 2.0 - Initialization Complete! / 初始化圆满完成！"
echo " Pre-configured demo accounts (Password: password123):"
echo "   - Administrator: admin      / password123"
echo "   - Lead Engineer: engineer1  / password123"
echo "   - Technician:    tech1      / password123"
echo ""
echo " Next Steps:"
echo "   * Run: ./2_start_foreground.sh (Interactive test on port 8000)"
echo "   * Run: sudo ./3_install_service.sh (Install background Systemd service)"
echo "======================================================================="
