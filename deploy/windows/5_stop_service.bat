@echo off
chcp 65001 >nul
title MaintainWise 2.0 - Stop Windows Service

echo Stopping MaintainWiseService...
net stop MaintainWiseService
echo.
echo Service stopped.
pause
