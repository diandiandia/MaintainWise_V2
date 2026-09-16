@echo off
chcp 65001 >nul
title MaintainWise 2.0 - Install Windows Background Service

echo =======================================================================
echo          MaintainWise 2.0 - Install Windows Service
echo =======================================================================
echo.
echo [*] Wrapping MaintainWise as Windows auto-start background service using WinSW...
echo [*] Notice: Administrator privilege required. Run as Administrator.
echo.

cd /d "%~dp0"

if exist "MaintainWiseService.exe" goto do_install

if exist "winsw.exe" (
    copy winsw.exe MaintainWiseService.exe >nul
    goto do_install
)

echo [*] Attempting to auto-download WinSW wrapper binary from GitHub...
powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; try { (New-Object Net.WebClient).DownloadFile('https://github.com/winsw/winsw/releases/download/v2.12.0/WinSW-x64.exe', 'MaintainWiseService.exe') } catch {}" 2>nul

if exist "MaintainWiseService.exe" goto do_install

echo.
echo [INFO] WinSW 自动下载受限 (GitHub 网络连接超时或处于离线局域网环境)。
echo.
echo 如需安装为 Windows 系统自启服务：
echo   1. 请手动下载 WinSW-x64.exe 或 WinSW-arm64.exe：
echo      https://github.com/winsw/winsw/releases
echo   2. 重命名为 MaintainWiseService.exe 放入 deploy\windows\ 目录；
echo   3. 再次运行本脚本即可一键安装服务。
echo.
echo -----------------------------------------------------------------------
echo 【强烈推荐】无需安装 Windows 服务，直接运行前台交互启动：
echo   直接在根目录运行:  maintainwise.bat test
echo   或双击:            deploy\windows\2_start_foreground.bat
echo   即可立即在端口 8000 体验完整全栈系统！
echo -----------------------------------------------------------------------
goto end

:do_install
MaintainWiseService.exe install
if %errorlevel% equ 0 (
    echo.
    echo ✅ Windows 服务安装成功！
    echo 服务名称: MaintainWiseService
    echo 可以运行 [4_start_service.bat] 或 maintainwise.bat start 启动服务。
) else (
    echo.
    echo ❌ 服务安装失败，请确保以管理员身份运行本脚本！
)

:end
echo.
pause
