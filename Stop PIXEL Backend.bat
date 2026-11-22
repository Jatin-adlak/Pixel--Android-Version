@echo off
setlocal
title PIXEL - Stopping backend
powershell.exe -NoLogo -NoProfile -ExecutionPolicy RemoteSigned -File "%~dp0scripts\stop-backend.ps1"
if errorlevel 1 (
    echo PIXEL could not stop. Read the message above.
    pause
    exit /b 1
)
echo Close the Expo CMD window before restarting Run PIXEL Phone.bat.
endlocal
