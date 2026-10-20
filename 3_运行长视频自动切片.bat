@echo off
cd /d "%~dp0"
title 长视频智能切片与影视解说自动化流水线 (5分钟左右中长切片)

set "PY="
if exist "C:\Program Files\Python311\python.exe" (
    set "PY=C:\Program Files\Python311\python.exe"
) else (
    set "PY=python"
)

"%PY%" "%~dp0long_to_shorts_pipeline.py" --duration 300 --max-clips 1

echo.
echo [完成] 按任意键打开成果文件夹并退出...
pause >nul
if exist "G:\矩阵短视频" (
    explorer.exe "G:\矩阵短视频"
) else (
    if exist "%~dp0长视频切片成果" explorer.exe "%~dp0长视频切片成果"
)