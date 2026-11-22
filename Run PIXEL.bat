@echo off
setlocal
title PIXEL - Starting project
if /i "%~1"=="phone" (
    if "%~2"=="" (
        powershell.exe -NoLogo -NoProfile -ExecutionPolicy RemoteSigned -File "%~dp0scripts\run-project.ps1" -Phone
    ) else (
        powershell.exe -NoLogo -NoProfile -ExecutionPolicy RemoteSigned -File "%~dp0scripts\run-project.ps1" -Phone -LanAddress "%~2"
    )
) else (
    powershell.exe -NoLogo -NoProfile -ExecutionPolicy RemoteSigned -File "%~dp0scripts\run-project.ps1"
)
if errorlevel 1 (
    echo.
    echo PIXEL could not start. Read the message above for details.
    pause
    exit /b 1
)
endlocal
