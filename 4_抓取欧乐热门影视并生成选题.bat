@echo off
cd /d "%~dp0"
title OLEVOD 热门影视抓取与吸睛爆款选题生成器

echo ========================================================
echo   正在连接 OLEVOD (欧乐影院) 抓取最新爆款影视作品...
echo ========================================================
echo.

set "PY="
if exist "C:\Program Files\Python311\python.exe" (
    set "PY=C:\Program Files\Python311\python.exe"
) else (
    set "PY=python"
)

"%PY%" "%~dp0fetch_olevod_hot.py"

echo.
echo ========================================================
echo [成功] 热门影视抓取完毕！已生成吸睛爆款选题。
echo 按任意键将自动用记事本打开 “今日爆款影视选题表.txt” 查看！
echo ========================================================
echo.
pause >nul
if exist "%~dp0今日爆款影视选题表.txt" notepad.exe "%~dp0今日爆款影视选题表.txt"