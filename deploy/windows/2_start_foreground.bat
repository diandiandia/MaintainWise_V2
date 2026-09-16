@echo off
chcp 65001 >nul
title MaintainWise 2.0 - Foreground Test Server (Port 8000)

echo =======================================================================
echo          MaintainWise 2.0 - Interactive Foreground Server
echo =======================================================================
echo.
echo [*] Starting single-port full-stack server (FastAPI + Vue3 SPA)...
echo [*] Local access:       http://127.0.0.1:8000
echo [*] Workshop LAN access: http://<Server_IP>:8000
echo.
echo Press Ctrl + C to terminate the foreground server.
echo.

cd /d "%~dp0..\..\backend"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir .
pause
