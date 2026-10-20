@echo off
cd /d "%~dp0"
title 首次扫码登录多平台 - 凭证保存

set "PY="
if exist "C:\Program Files\Python311\python.exe" (
    set "PY=C:\Program Files\Python311\python.exe"
) else (
    set "PY=python"
)

"%PY%" "%~dp0login_platforms.py"
echo.
pause
