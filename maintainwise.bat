@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set "ACTION=%~1"
set "BASE_DIR=%~dp0"

if "%ACTION%"=="" goto usage
if /i "%ACTION%"=="help" goto usage
if /i "%ACTION%"=="-h" goto usage
if /i "%ACTION%"=="--help" goto usage

if /i "%ACTION%"=="deploy" (
    call "%BASE_DIR%deploy\windows\0_deploy_all.bat"
    goto end
)
if /i "%ACTION%"=="start" (
    call "%BASE_DIR%deploy\windows\4_start_service.bat"
    goto end
)
if /i "%ACTION%"=="stop" (
    call "%BASE_DIR%deploy\windows\5_stop_service.bat"
    goto end
)
if /i "%ACTION%"=="restart" (
    call "%BASE_DIR%deploy\windows\5_stop_service.bat"
    call "%BASE_DIR%deploy\windows\4_start_service.bat"
    goto end
)
if /i "%ACTION%"=="status" (
    echo =======================================================================
    echo        MaintainWise 2.0 - Windows 服务状态
    echo =======================================================================
    sc query MaintainWiseService
    netstat -ano | findstr 8000
    goto end
)
if /i "%ACTION%"=="backup" (
    call "%BASE_DIR%deploy\windows\7_backup_now.bat"
    goto end
)

echo.
echo ❌ 未知参数: %ACTION%
echo.

:usage
echo =======================================================================
echo        MaintainWise 2.0 - Windows 命令行总控入口
echo =======================================================================
echo 用法 (Usage):
echo   maintainwise.bat ^<action^>  或  mw.bat ^<action^>
echo.
echo 常用指令 (Commands):
echo   deploy   一键全自动依赖安装与环境初始化向导
echo   start    启动 Windows 后台自启系统服务 (net start)
echo   stop     停止 Windows 后台系统服务 (net stop)
echo   restart  重启 Windows 后台系统服务
echo   status   查看 Windows 服务运行状态与端口监听
echo   backup   立即执行一次 SQLite WAL 全量热备份
echo   help     查看本帮助信息
echo =======================================================================

:end
endlocal
