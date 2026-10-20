# -*- coding: utf-8 -*-
"""
自媒体全球多平台免密凭证配置与登录管理器 (v2.0 智能无阻塞防闪退版)
支持：
  1. 📕 小红书创作服务平台 (xiaohongshu)
  2. ✖️ X (Twitter) (twitter_x)
  3. 📸 Instagram (instagram)
  4. 🎬 YouTube 创作者后台 (youtube)
  5. 🎵 抖音创作者中心 (douyin)

改进特性：
- 解决 GUI 调用时由于 stdin=DEVNULL 导致 input() 报 EOFError 进而瞬间闪退关闭浏览器的严重缺陷
- 自动智能检测是否登录成功 (实时 URL / 用户头像 / 核心元素识别)
- 智能监听浏览器窗口：用户完成登录后直接关闭浏览器即可完成凭证永久写入
"""

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
os.makedirs(DATA_DIR, exist_ok=True)

PLATFORMS = {
    "1": {
        "key": "xiaohongshu",
        "name": "📕 小红书创作服务平台",
        "url": "https://creator.xiaohongshu.com/",
        "folder": "xiaohongshu",
        "guide": "请使用手机【小红书 App】扫码完成登录；"
    },
    "2": {
        "key": "twitter_x",
        "name": "✖️ X (Twitter) 官方网页版",
        "url": "https://x.com/login",
        "folder": "twitter_x",
        "guide": "请在打开的页面中输入您的 X 账号密码登录；"
    },
    "3": {
        "key": "instagram",
        "name": "📸 Instagram (IG) 网页版",
        "url": "https://www.instagram.com/accounts/login/",
        "folder": "instagram",
        "guide": "请在打开的页面中输入您的 Instagram 账号密码登录；"
    },
    "4": {
        "key": "youtube",
        "name": "🎬 YouTube 创作者工作室 (Studio)",
        "url": "https://studio.youtube.com/",
        "folder": "youtube",
        "guide": "请在打开的 Google 登录页面登录您的 YouTube 创作者账号；"
    },
    "5": {
        "key": "douyin",
        "name": "🎵 抖音创作者中心",
        "url": "https://creator.douyin.com/",
        "folder": "douyin",
        "guide": "请使用手机【抖音 App】扫码完成登录；"
    }
}

KEY_MAP = {
    "xiaohongshu": "1",
    "red": "1",
    "xhs": "1",
    "x": "2",
    "twitter": "2",
    "twitter_x": "2",
    "ig": "3",
    "instagram": "3",
    "yt": "4",
    "youtube": "4",
    "douyin": "5",
    "dy": "5"
}

def login_platform(p, platform_info):
    name = platform_info["name"]
    url = platform_info["url"]
    folder = platform_info["folder"]
    guide = platform_info["guide"]
    profile_dir = os.path.join(DATA_DIR, folder)
    os.makedirs(profile_dir, exist_ok=True)

    print(f"\n" + "=" * 65)
    print(f"🚀 正在启动 Edge 浏览器打开【{name}】...")
    print(f">> 数据保存路径: {profile_dir}")
    print(f"=" * 65)

    try:
        context = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            channel="msedge",
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized"
            ],
            no_viewport=True
        )
    except Exception as e:
        print(f"[!] 启动 Edge 遇到占用，尝试标准启动: {e}")
        context = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=False,
            args=["--start-maximized"],
            no_viewport=True
        )

    page = context.pages[0] if context.pages else context.new_page()
    page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    print(f">> 正在导航至: {url}")
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
    except Exception as e:
        print(f"[!] 网页加载提示: {e}")

    print("\n--------------------------------------------------------")
    print(f"👉 【请在已弹出的 Edge 浏览器中完成以下操作】")
    print(f"👉 1. {guide}")
    print(f"👉 2. 登录成功后，您可以继续浏览，或【直接关闭该浏览器窗口】；")
    print(f"👉 3. 关闭窗口后系统将自动保存所有登录凭证与 Cookies！")
    print("--------------------------------------------------------\n")

    start_time = time.time()
    login_detected = False

    # 循环监听，绝不因为 stdin 关闭而闪退
    while True:
        try:
            if page.is_closed() or not context.pages:
                print(f"\n[√] 浏览器窗口已由用户关闭。")
                break
        except Exception:
            break

        # 智能检测登录状态
        if not login_detected:
            try:
                curr_url = page.url.lower()
                if folder == "xiaohongshu":
                    if "creator.xiaohongshu.com" in curr_url and "login" not in curr_url:
                        if page.locator('text="发布笔记", text="上传视频", text="创作服务", .user-avatar, .name-box').count() > 0:
                            login_detected = True
                elif folder == "twitter_x":
                    if ("x.com/home" in curr_url or "twitter.com/home" in curr_url or "compose" in curr_url) and "login" not in curr_url:
                        login_detected = True
                elif folder == "instagram":
                    if "instagram.com" in curr_url and "accounts/login" not in curr_url:
                        if page.locator('svg[aria-label="Home"], svg[aria-label="首页"], [aria-label="Direct"]').count() > 0:
                            login_detected = True
                elif folder == "youtube":
                    if "studio.youtube.com" in curr_url and "accounts.google.com" not in curr_url and "signin" not in curr_url:
                        login_detected = True
                elif folder == "douyin":
                    if "creator.douyin.com" in curr_url and "login" not in curr_url:
                        login_detected = True

                if login_detected:
                    print(f"\n🎉 [识别成功] 恭喜！系统已自动检测到【{name}】登录成功！")
                    print(f">> 登录 Cookie 与凭证已永久写入本地。")
                    print(f">> 您可以关闭浏览器窗口，或在控制台继续使用矩阵发布。\n")
            except Exception:
                pass

        time.sleep(1)

        # 超过 15 分钟无动作自动安全退出
        if time.time() - start_time > 900:
            print("[提示] 登录等待已达到 15 分钟上限，自动保存当前状态...")
            break

    try:
        context.close()
    except Exception:
        pass

    print(f"\n[√] 【{name}】登录凭证已永久保存在本地: {profile_dir}！")
    print(f">> 后续全自动发布将完全免登录、免扫码运行。\n")

def main():
    target_key = None
    if len(sys.argv) > 1:
        raw_arg = sys.argv[1].lower().strip("-/")
        if raw_arg in KEY_MAP:
            target_key = KEY_MAP[raw_arg]
        elif raw_arg in PLATFORMS:
            target_key = raw_arg

    with sync_playwright() as p:
        if target_key and target_key in PLATFORMS:
            login_platform(p, PLATFORMS[target_key])
            return

        while True:
            print("\n========================================================")
            print("     🔑 全球多平台自媒体登录与凭证永久保存工具")
            print("========================================================")
            print("说明：调用本机 Edge 浏览器，登录后凭证永久保存在本地。\n")

            for k, v in PLATFORMS.items():
                cookie_exists = os.path.exists(os.path.join(DATA_DIR, v["folder"]))
                status = " (已配置环境)" if cookie_exists else ""
                print(f"  [{k}] {v['name']}{status}")

            print("  [A] 顺序配置全部矩阵平台 (1➔2➔3➔4)")
            print("  [Q] 退出")
            print("--------------------------------------------------------")

            try:
                choice = input(">> 请输入平台序号 [1-5 / A / Q]: ").strip().upper()
            except (EOFError, KeyboardInterrupt):
                break

            if choice == "Q" or not choice:
                break
            elif choice == "A":
                for k in ["1", "2", "3", "4"]:
                    login_platform(p, PLATFORMS[k])
                break
            elif choice in PLATFORMS:
                login_platform(p, PLATFORMS[choice])
            else:
                print("[错误] 无效的序号，请重新输入！")

    print("\n[√] 平台配置流程已结束。\n")

if __name__ == "__main__":
    main()
