@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 自媒体全自动工厂 - 全球多平台总控台

echo 正在唤醒全球多平台自媒体工厂控制面板...

set "PY="
if exist "C:\Program Files\Python311\python.exe" (
    set "PY=C:\Program Files\Python311\python.exe"
) else (
    set "PY=python"
)

"%PY%" dashboard.py