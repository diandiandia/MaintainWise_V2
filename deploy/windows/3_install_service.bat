@echo off
chcp 65001 >nul
title MaintainWise 2.0 - Install Windows Background Service

echo =======================================================================
echo          MaintainWise 2.0 - Install Windows Service
echo =======================================================================
echo.
echo [*] Wrapping MaintainWise as Windows auto-start background service using WinSW...
echo [*] Notice: Administrator privilege required. Run as Administrator!
echo.

cd /d "%~dp0"
if not exist "MaintainWiseService.exe" (
    if exist "winsw.exe" (
        copy winsw.exe MaintainWiseService.exe >nul
    ) else (
        echo [*] Attempting to auto-download WinSW wrapper binary...
        powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('https://github.com/winsw/winsw/releases/download/v2.12.0/WinSW-x64.exe', 'MaintainWiseService.exe')" 2>nul
        if not exist "MaintainWiseService.exe" (
            echo [INFO] Automatic download unavailable (offline network).
            echo Please manually download WinSW-x64.exe from:
            echo   https://github.com/winsw/winsw/releases
            echo and place it into this directory named as: MaintainWiseService.exe
        )
    )
)

if exist "MaintainWiseService.exe" (
    MaintainWiseService.exe install
    echo.
    echo Service installed successfully!
    echo Service name: MaintainWiseService
    echo You can run [4_start_service.bat] to start it.
) else (
    echo.
    echo [Alternative] You can run [2_start_foreground.bat] directly or use Windows Task Scheduler.
)

echo.
pause
