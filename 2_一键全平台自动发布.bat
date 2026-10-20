@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 全球自媒体矩阵自动化发布 - 小红书 / X / Instagram / YouTube

echo ========================================================
echo   🚀 正在唤醒自媒体全球矩阵全自动发布引擎...
echo   目标平台: 小红书 + X(Twitter) + Instagram + YouTube
echo   (已停用微信视频号)
echo ========================================================
echo.

set "PY="
if exist "C:\Program Files\Python311\python.exe" (
    set "PY=C:\Program Files\Python311\python.exe"
) else (
    set "PY=python"
)

"%PY%" "%~dp0publish_multi_platform.py" --count 2

echo.
echo ========================================================
echo   矩阵发布流程结束。
echo ========================================================
pause
