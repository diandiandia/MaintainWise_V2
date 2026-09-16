@echo off
chcp 65001 >nul
title MaintainWise 2.0 - Windows Environment Initialization

echo =======================================================================
echo          MaintainWise 2.0 - Environment Initialization
echo =======================================================================
echo.
echo [1/3] Checking Python environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not detected! Please install Python 3.10+ and check 'Add Python to PATH'.
    pause
    exit /b 1
)
python --version

echo.
echo [2/3] Installing application dependencies...
if not exist "%~dp0..\..\backend\requirements.txt" (
    echo [*] Generating default requirements.txt automatically...
    (
        echo fastapi^>=0.100.0
        echo uvicorn^>=0.23.0
        echo pydantic^>=2.0.0
        echo pydantic-settings^>=2.0.0
        echo pyjwt^>=2.8.0
        echo bcrypt^>=4.0.0
        echo python-multipart^>=0.0.6
        echo aiofiles^>=23.0.0
        echo qrcode^>=7.4.2
        echo pillow^>=10.0.0
        echo pytest^>=7.0.0
        echo httpx^>=0.24.0
    ) > "%~dp0..\..\backend\requirements.txt"
)

python -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple >nul 2>&1
python -m pip install -r "%~dp0..\..\backend\requirements.txt" -i https://pypi.tuna.tsinghua.edu.cn/simple
if %errorlevel% neq 0 (
    echo [WARN] Tsinghua PyPI mirror failed, retrying with official PyPI...
    python -m pip install -r "%~dp0..\..\backend\requirements.txt"
)

echo.
echo [3/3] Initializing SQLite 3 WAL database and seed data...
cd /d "%~dp0..\..\backend"
python -c "from app.db.init_db import init_db; init_db(); print('[OK] Database and demo data initialized successfully!')"

echo.
echo =======================================================================
echo  MaintainWise 2.0 Initialization Complete!
echo  Default accounts (Password: password123):
echo    - Administrator: admin      / password123
echo    - Lead Engineer: engineer1  / password123
echo    - Technician:    tech1      / password123
echo.
echo  Next Step: Double-click [2_start_foreground.bat] to test.
echo =======================================================================
pause
