@echo off
setlocal
title PIXEL - Prepare GitHub source
if not exist "%~dp0backend\.venv\Scripts\python.exe" (
    echo Run Setup PIXEL.bat first.
    pause
    exit /b 1
)
"%~dp0backend\.venv\Scripts\python.exe" "%~dp0scripts\prepare-github.py"
if errorlevel 1 (
    echo Export stopped. Review the message above. No code was published.
    pause
    exit /b 1
)
pause
endlocal
