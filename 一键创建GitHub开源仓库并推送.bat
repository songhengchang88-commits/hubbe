@echo off
chcp 65001 >nul
title GitHub 开源自动化推送助手
cd /d "C:\Users\Administrator\Desktop\自媒体全自动工厂"
echo ========================================================
echo   🎬 AutoMedia-Factory 一键创建并推送到 GitHub 开源仓库
echo ========================================================
echo.
gh auth status
if %errorlevel% neq 0 (
    echo [提示] 尚未完成登录，正在调起浏览器授权...
    gh auth login --hostname github.com -p https --web
)
echo.
echo [1/2] 正在连接 GitHub 并创建公开开源仓库 AutoMedia-Factory...
gh repo create AutoMedia-Factory --public --source=. --remote=origin --description "全自动 AI 影视解说切片制作 · 跨平台矩阵分发引擎 · 24小时无人值守短视频工厂"
echo.
echo [2/2] 正在推送代码至 GitHub main 分支...
git push -u origin main
echo.
echo ========================================================
echo 🎉 恭喜！项目已成功开源发布到 GitHub！
echo ========================================================
pause
