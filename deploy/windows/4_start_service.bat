@echo off
chcp 65001 >nul
title MaintainWise 2.0 - Start Windows Service

echo Starting MaintainWiseService...
net start MaintainWiseService
if %errorlevel% equ 0 (
    echo.
    echo Service started successfully!
    echo Access URL: http://127.0.0.1:8000
) else (
    echo.
    echo [INFO] If service is not installed, please run [3_install_service.bat] first,
    echo or run [2_start_foreground.bat] directly.
)
pause
