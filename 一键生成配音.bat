@echo off
cd /d "%~dp0"
title 自媒体全自动配音助手

set "PY="
if exist "C:\Program Files\Python311\python.exe" (
    set "PY=C:\Program Files\Python311\python.exe"
) else (
    set "PY=python"
)

"%PY%" "%~dp0generate_voice.py"
echo.
pause
