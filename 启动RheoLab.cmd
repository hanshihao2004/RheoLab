@echo off
setlocal
chcp 65001 >nul
title RheoLab
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_rheolab.ps1"
if errorlevel 1 (
    echo.
    pause
)
endlocal
