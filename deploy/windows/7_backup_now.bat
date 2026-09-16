@echo off
chcp 65001 >nul
title MaintainWise 2.0 - Live Hot Backup Execution

echo =======================================================================
echo          MaintainWise 2.0 - Live Hot Backup Execution
echo =======================================================================
echo.
echo Archiving SQLite 3 WAL database and uploaded media assets...
cd /d "%~dp0..\..\backend"
python -c "from app.services.backup_service import execute_system_backup; res = execute_system_backup(); print('Backup complete! File:', res['backup_file'], 'Path:', res['backup_path'], 'Size:', res['size_bytes'], 'bytes')"

echo.
echo Backup archive saved to data\backups.
echo You can schedule this script via Windows Task Scheduler.
echo.
pause
