@echo off
chcp 65001 >nul
title MaintainWise 2.0 - Windows Automated Deployment Wizard

echo =======================================================================
echo        MaintainWise 2.0 - Windows Automated Deployment
echo =======================================================================
echo.

:: Step 1: Initialize Environment
call "%~dp01_init_env.bat"

echo.
echo -----------------------------------------------------------------------
echo Select Startup Mode / 请选择启动方式：
echo   [1] Start Interactive Foreground Test (Recommended for first run)
echo       立即前台交互测试启动 (端口 8000)
echo   [2] Install & Start Background Service (Production, Admin required)
echo       安装并启动为 Windows 后台自启服务
echo   [3] Exit now (Environment is ready)
echo       仅完成环境初始化，稍后自行启动
echo -----------------------------------------------------------------------
set /p CHOICE=Please select [1-3] (Default 1): 
if "%CHOICE%"=="" set CHOICE=1

if "%CHOICE%"=="1" (
    echo Starting foreground test service...
    call "%~dp02_start_foreground.bat"
) else if "%CHOICE%"=="2" (
    echo Installing and starting Windows service...
    call "%~dp03_install_service.bat"
    call "%~dp04_start_service.bat"
) else (
    echo Initialization complete. You can use batch files in deploy\windows.
    pause
)
