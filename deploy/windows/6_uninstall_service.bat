@echo off
chcp 65001 >nul
title MaintainWise 2.0 - Uninstall Windows Service

echo Uninstalling MaintainWiseService...
net stop MaintainWiseService >nul 2>&1
cd /d "%~dp0"
if exist "MaintainWiseService.exe" (
    MaintainWiseService.exe uninstall
    echo Service uninstalled successfully.
) else (
    echo MaintainWiseService.exe not found.
)
pause
