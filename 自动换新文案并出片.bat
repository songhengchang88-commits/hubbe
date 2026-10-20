@echo off
cd /d "%~dp0"
title 自动换新文案并出片 - 全自动工厂流水线

set "PY="
if exist "C:\Program Files\Python311\python.exe" (
    set "PY=C:\Program Files\Python311\python.exe"
) else (
    set "PY=python"
)

"%PY%" "%~dp0auto_refresh_and_produce.py"

echo.
echo [完成] 5秒后窗口将自动关闭...
ping 127.0.0.1 -n 6 >nul
