@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set "ACTION=%~1"
set "BASE_DIR=%~dp0"

if "%ACTION%"=="" goto menu
if /i "%ACTION%"=="help" goto menu
if /i "%ACTION%"=="-h" goto menu
if /i "%ACTION%"=="--help" goto menu

if /i "%ACTION%"=="deploy" goto do_deploy
if /i "%ACTION%"=="test" goto do_test
if /i "%ACTION%"=="start" goto do_start
if /i "%ACTION%"=="stop" goto do_stop
if /i "%ACTION%"=="restart" goto do_restart
if /i "%ACTION%"=="status" goto do_status
if /i "%ACTION%"=="backup" goto do_backup

echo.
echo ❌ 未知参数: %ACTION%
echo.

:menu
echo =======================================================================
echo        MaintainWise 2.0 - Windows 命令行与交互总控入口
echo =======================================================================
echo 用法 (Usage):
echo   maintainwise.bat ^<action^>  或  mw.bat ^<action^>
echo.
echo 可选指令 (Commands):
echo   [1] deploy   一键全自动依赖安装与环境初始化向导
echo   [2] test     前台交互测试启动 (推荐初次运行/实时查看日志)
echo   [3] start    启动 Windows 后台自启系统服务 (net start)
echo   [4] stop     停止 Windows 后台系统服务 (net stop)
echo   [5] restart  重启 Windows 后台系统服务
echo   [6] status   查看 Windows 服务运行状态与端口监听
echo   [7] backup   立即执行一次 SQLite WAL 全量热备份
echo   [0] exit     退出
echo =======================================================================
set /p "CHOICE=请输入指令选项编号或直接输入指令 [0-7] (默认 1): "
if "%CHOICE%"=="" set CHOICE=1

if "%CHOICE%"=="1" goto do_deploy
if /i "%CHOICE%"=="deploy" goto do_deploy
if "%CHOICE%"=="2" goto do_test
if /i "%CHOICE%"=="test" goto do_test
if "%CHOICE%"=="3" goto do_start
if /i "%CHOICE%"=="start" goto do_start
if "%CHOICE%"=="4" goto do_stop
if /i "%CHOICE%"=="stop" goto do_stop
if "%CHOICE%"=="5" goto do_restart
if /i "%CHOICE%"=="restart" goto do_restart
if "%CHOICE%"=="6" goto do_status
if /i "%CHOICE%"=="status" goto do_status
if "%CHOICE%"=="7" goto do_backup
if /i "%CHOICE%"=="backup" goto do_backup
if "%CHOICE%"=="0" goto end
if /i "%CHOICE%"=="exit" goto end
goto end

:do_deploy
call "%BASE_DIR%deploy\windows\0_deploy_all.bat"
goto end

:do_test
call "%BASE_DIR%deploy\windows\2_start_foreground.bat"
goto end

:do_start
call "%BASE_DIR%deploy\windows\4_start_service.bat"
goto end

:do_stop
call "%BASE_DIR%deploy\windows\5_stop_service.bat"
goto end

:do_restart
call "%BASE_DIR%deploy\windows\5_stop_service.bat"
call "%BASE_DIR%deploy\windows\4_start_service.bat"
goto end

:do_status
echo =======================================================================
echo        MaintainWise 2.0 - Windows 服务状态
echo =======================================================================
sc query MaintainWiseService
echo.
echo 端口 8000 监听状态：
netstat -ano | findstr 8000
echo =======================================================================
pause
goto end

:do_backup
call "%BASE_DIR%deploy\windows\7_backup_now.bat"
goto end

:end
endlocal
