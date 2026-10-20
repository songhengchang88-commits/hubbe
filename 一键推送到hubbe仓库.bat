@echo off
chcp 65001 >nul
title 推送 AutoMedia-Factory 到 GitHub (hubbe 仓库)
cd /d "%~dp0"

echo ==============================================================================
echo       🎬 AutoMedia-Factory 正在推送至 GitHub 仓库:
echo       👉 https://github.com/songhengchang88-commits/hubbe
echo ==============================================================================
echo.
echo [1/3] 配置远程仓库关联...
git remote set-url origin https://github.com/songhengchang88-commits/hubbe.git
git config user.name "songhengchang88-commits"
git config user.email "songhengchang88@gmail.com"
echo [√] 远程地址已配置: https://github.com/songhengchang88-commits/hubbe.git
echo.

echo [2/3] 准备推送选项:
echo 1. 直接通过浏览器/Git凭证助手推送 (推荐，回车直接开始)
echo 2. 输入 GitHub Personal Access Token (PAT) 推送
echo.
set /p CHOICE="请选择 [直接回车执行方式 1]: "

if "%CHOICE%"=="2" (
    echo.
    set /p MY_TOKEN="请输入您的 GitHub Token (ghp_...): "
    if not "%MY_TOKEN%"=="" (
        git remote set-url origin https://songhengchang88-commits:%MY_TOKEN%@github.com/songhengchang88-commits/hubbe.git
    )
)

echo.
echo [3/3] 正在推送代码至 GitHub main 分支...
git push -u origin main --force

if %errorlevel% equ 0 (
    echo.
    echo ==============================================================================
    echo 🎉🎉🎉 恭喜！项目已成功推送并完全开源！
    echo 仓库主页: https://github.com/songhengchang88-commits/hubbe
    echo ==============================================================================
) else (
    echo.
    echo [!] 推送遇到阻碍。如果弹出了 GitHub 登录窗口，请点击并在浏览器中确认授权。
)

echo.
echo 按任意键退出...
pause >nul
