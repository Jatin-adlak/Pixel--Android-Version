@echo off
setlocal
title PIXEL - Enable local phone access
powershell.exe -NoLogo -NoProfile -ExecutionPolicy RemoteSigned -File "%~dp0scripts\request-phone-access.ps1"
if errorlevel 1 (
    echo Phone access could not be enabled. Windows administrator approval is required.
    pause
    exit /b 1
)
pause
endlocal
