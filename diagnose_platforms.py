# -*- coding: utf-8 -*-
import os
import sys
import time
from playwright.sync_api import sync_playwright

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "browser_data")
TEMP_DIR = os.path.join(BASE_DIR, "temp_pipeline")
os.makedirs(TEMP_DIR, exist_ok=True)

TARGETS = [
    {
        "id": "xiaohongshu",
        "name": "小红书",
        "folder": "xiaohongshu",
        "url": "https://creator.xiaohongshu.com/publish/publish",
        "login_check": lambda page: "login" not in page.url.lower() and page.locator('text="上传视频", text="发布笔记", .user-avatar').count() > 0
    },
    {
        "id": "twitter_x",
        "name": "X (Twitter)",
        "folder": "twitter_x",
        "url": "https://x.com/compose/post",
        "login_check": lambda page: "login" not in page.url.lower() and page.locator('text="Sign in", text="登录"').count() == 0
    },
    {
        "id": "instagram",
        "name": "Instagram",
        "folder": "instagram",
        "url": "https://www.instagram.com/",
        "login_check": lambda page: "accounts/login" not in page.url.lower() and page.locator('input[name="username"]').count() == 0
    },
    {
        "id": "youtube",
        "name": "YouTube",
        "folder": "youtube",
        "url": "https://studio.youtube.com/",
        "login_check": lambda page: "accounts.google.com" not in page.url.lower() and "signin" not in page.url.lower()
    }
]

def diagnose():
    print("=" * 65)
    print("🔍 [自媒体矩阵全平台实时诊断与监控探针启动]")
    print("=" * 65)

    with sync_playwright() as p:
        for t in TARGETS:
            name = t["name"]
            folder = t["folder"]
            url = t["url"]
            profile_dir = os.path.join(DATA_DIR, folder)

            print(f"\n▶ 正在诊断平台: 【{name}】...")
            print(f"   Profile 目录: {profile_dir}")
            
            try:
                # 尝试以 headless=True 快速探活
                context = p.chromium.launch_persistent_context(
                    user_data_dir=profile_dir,
                    channel="msedge",
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled"]
                )
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(3)

                curr_url = page.url
                curr_title = page.title()
                is_logged_in = t["login_check"](page)

                shot_path = os.path.join(TEMP_DIR, f"diag_{folder}.png")
                page.screenshot(path=shot_path)

                status_str = "🟢 已成功登录并就绪！" if is_logged_in else "⚪ 处于未登录状态/需要登录"
                print(f"   当前 URL: {curr_url}")
                print(f"   页面标题: {curr_title}")
                print(f"   状态判定: {status_str}")
                print(f"   页面截图: {shot_path}")

                context.close()
            except Exception as e:
                print(f"   [!] 探活异常: {e}")

    print("\n" + "=" * 65)
    print("🎉 诊断完成！")
    print("=" * 65)

if __name__ == "__main__":
    diagnose()
