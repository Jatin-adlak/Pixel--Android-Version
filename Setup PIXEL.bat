@echo off
setlocal
title PIXEL - First-time setup
powershell.exe -NoLogo -NoProfile -ExecutionPolicy RemoteSigned -File "%~dp0scripts\setup-project.ps1"
if errorlevel 1 (
    echo Read the setup message above, correct it, then run this file again.
    pause
    exit /b 1
)
pause
endlocal
