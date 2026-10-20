@echo off
chcp 65001 >nul
title AutoMedia-Factory GitHub 开源发布助手
cd /d "%~dp0"

echo ==============================================================================
echo       🎬 AutoMedia-Factory (自媒体全自动矩阵工厂) - GitHub 开源一键发布
echo ==============================================================================
echo.
echo [1/3] 检查本地代码与 Git 仓库状态...
git status >nul 2>&1
if %errorlevel% neq 0 (
    git init
    git branch -M main
    git add .
    git commit -m "feat: initial open-source release of AutoMedia-Factory v5.0"
)
echo [√] 本地代码版本已准备就绪 (已安全隔离所有私密 Cookie、密码及大视频)。
echo.

echo [2/3] 检查 GitHub 登录凭证...
gh auth status >nul 2>&1
if %errorlevel% neq 0 (
    echo [提示] 尚未检测到 GitHub 登录状态，现在为您调起快速授权...
    echo 👉 请按照终端提示输入验证码，并在打开的浏览器页面中点击 Authorize 确认：
    echo.
    gh auth login --hostname github.com -p https --web
) else (
    echo [√] GitHub 账号已处于登录状态！
)

echo.
echo [3/3] 开始在 GitHub 创建公开开源仓库并自动推送...
echo.
set /p REPO_NAME="请输入您想创建的 GitHub 仓库名称 [直接回车默认: AutoMedia-Factory]: "
if "%REPO_NAME%"=="" set REPO_NAME=AutoMedia-Factory

gh repo create %REPO_NAME% --public --source=. --remote=origin --push --description "全自动 AI 影视解说切片制作 · 跨平台矩阵分发引擎 · 24小时无人值守短视频工厂"

if %errorlevel% equ 0 (
    echo.
    echo ==============================================================================
    echo 🎉🎉🎉 恭喜！项目已成功在 GitHub 上完全开源并推送完毕！
    echo 仓库地址已生成，请在浏览器中查看您的开源成果！
    echo ==============================================================================
) else (
    echo.
    echo [提示] 如果仓库此前已在网页端建好，正在尝试直接推送...
    git push -u origin main
)

echo.
echo 按任意键退出...
pause >nul
