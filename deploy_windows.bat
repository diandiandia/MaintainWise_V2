@echo off
chcp 65001 >nul
title MaintainWise 2.0 - Windows One-Click Deployment

call "%~dp0deploy\windows\0_deploy_all.bat"
