# -*- coding: utf-8 -*-
"""
自媒体多平台全自动发布工具
支持自动将【成品视频.mp4】发布至：抖音、小红书、微信视频号
自动填入【发布标题与标签.txt】中的标题与热门话题标签
"""

import os
import sys
import time
from playwright.sync_api import sync_playwright

# 兼容 Windows 控制台输出编码
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "browser_data")
VIDEO_FILE = os.path.join(BASE_DIR, "成品视频.mp4")
META_FILE = os.path.join(BASE_DIR, "发布标题与标签.txt")

def load_video_and_meta():
    """读取待发布视频及文案标题与标签"""
    g_video = r"G:\矩阵短视频\成品视频.mp4"
    target_video = g_video if os.path.exists(g_video) else VIDEO_FILE

    if not os.path.exists(target_video):
        print(f"\n[错误] 未找到视频文件: {target_video}")
        print("请先双击运行【一键生成视频.bat】生成成品视频后再来发布！")
        sys.exit(1)

    title = "成年人最大的自律：收起廉价的善良，不在烂人烂事上消耗自己"
    tags = "#认知觉醒 #人性 #深夜感悟 #情感共鸣"

    if os.path.exists(META_FILE):
        for enc in ["utf-8-sig", "utf-8", "gbk", "gb18030"]:
            try:
                with open(META_FILE, "r", encoding=enc) as f:
                    lines = [line.strip() for line in f if line.strip()]
                    if lines:
                        title = lines[0]
                    if len(lines) > 1:
                        tags = lines[1]
                break
            except Exception:
                continue

    return target_video, title, tags

def get_browser_context(p, folder_name):
    """启动带持久化 Cookie 的 Edge 浏览器上下文"""
    profile_dir = os.path.join(DATA_DIR, folder_name)
    os.makedirs(profile_dir, exist_ok=True)
    
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
    page = context.pages[0] if context.pages else context.new_page()
    page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return context, page

def publish_douyin(p, video_path, title, tags, auto_click=True):
    """抖音创作者中心自动发布"""
    print("\n--------------------------------------------------------")
    print("▶ [1/3] 正在启动【抖音】发布流程...")
    print("--------------------------------------------------------")
    context, page = get_browser_context(p, "douyin")
    try:
        url = "https://creator.douyin.com/creator-micro/content/upload"
        print(f">> 正在打开抖音视频上传页: {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        time.sleep(3)

        # 检查是否在登录页面
        if "login" in page.url or page.locator('text="扫码登录"').count() > 0:
            print("\n[!] 提示：检测到当前抖音尚未登录！")
            print("👉 请在弹出的浏览器中扫码登录，登录后请按回车继续；")
            print("👉 建议下次先运行【1_首次扫码登录各平台.bat】一次性配置好！")
            input(">> 扫码完成后按回车 [Enter] 继续: ")

        # 1. 查找并上传视频
        print(">> 正在自动上传视频文件...")
        try:
            file_input = page.wait_for_selector('input[type="file"]', timeout=15000)
            file_input.set_input_files(video_path)
            print(">> 视频文件已填入上传组件，正在等待平台解析...")
        except Exception as e:
            print(f"[!] 未直接找到常规上传框 ({e})，正在尝试全局查找...")
            page.set_input_files('input[type="file"]', video_path)

        time.sleep(4)

        # 2. 填写简介和标签
        print(">> 正在自动填写作品简介与热门话题...")
        content_text = f"{title} {tags}"
        filled = False

        # 尝试常见的富文本/contenteditable输入框
        desc_selectors = [
            'div[contenteditable="true"]',
            '.zone-container',
            'textarea',
            'div[placeholder*="作品简介"]'
        ]
        for sel in desc_selectors:
            loc = page.locator(sel).first
            if loc.count() > 0 and loc.is_visible():
                try:
                    loc.click()
                    page.keyboard.press("Control+A")
                    page.keyboard.press("Backspace")
                    page.keyboard.type(content_text, delay=20)
                    filled = True
                    print(">> 简介与标签已成功填入！")
                    break
                except Exception:
                    continue

        if not filled:
            print("[!] 未能自动定位简介输入框，请在浏览器中核对简介内容。")

        # 3. 等待视频上传并点击发布
        if auto_click:
            print(">> 正在定位【发布】按钮...")
            time.sleep(5)
            pub_btn = page.locator('button:has-text("发布")').first
            if pub_btn.count() > 0:
                # 等待按钮可点击
                try:
                    pub_btn.scroll_into_view_if_needed()
                    pub_btn.click(timeout=10000)
                    print("\n[√] 抖音视频已成功自动点击【发布】！")
                    time.sleep(3)
                except Exception as e:
                    print(f"[!] 自动点击发布遇到阻碍 ({e})，请在浏览器中确认点击。")
            else:
                print("[!] 未找到发布按钮，请在浏览器中核对后手动点击发布。")
        else:
            print("\n[提示] 已为您自动上传并填好内容，请在浏览器中检查确认后手动点击发布。")
            input(">> 确认发布后，请按回车继续... ")

    except Exception as e:
        print(f"\n[错误] 抖音发布过程中出现异常: {e}")
    finally:
        time.sleep(2)
        context.close()
        print(">> 抖音发布任务执行完毕，浏览器已安全退出。")

def publish_xiaohongshu(p, video_path, title, tags, auto_click=True):
    """小红书创作服务平台自动发布"""
    print("\n--------------------------------------------------------")
    print("▶ [2/3] 正在启动【小红书】发布流程...")
    print("--------------------------------------------------------")
    context, page = get_browser_context(p, "xiaohongshu")
    try:
        url = "https://creator.xiaohongshu.com/publish/publish"
        print(f">> 正在打开小红书发布页面: {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        time.sleep(3)

        # 检查登录
        if "login" in page.url or page.locator('text="登录"').count() > 2:
            print("\n[!] 提示：检测到当前小红书尚未登录！")
            input(">> 请在浏览器中扫码登录，完成后回到此处按回车 [Enter] 继续: ")

        # 切换到“上传视频”标签（如果是默认图文）
        video_tab = page.locator('text="上传视频"').first
        if video_tab.count() > 0 and video_tab.is_visible():
            try:
                video_tab.click()
                time.sleep(1)
            except Exception:
                pass

        # 1. 上传视频
        print(">> 正在自动上传视频文件...")
        try:
            file_input = page.wait_for_selector('input[type="file"]', timeout=15000)
            file_input.set_input_files(video_path)
            print(">> 视频文件已填入小红书上传组件...")
        except Exception as e:
            print(f"[!] 上传组件定位微调: {e}")
            page.set_input_files('input[type="file"]', video_path)

        time.sleep(4)

        # 2. 填写标题 (小红书限长 20 字)
        print(">> 正在自动填写笔记标题 (截取前20字)...")
        short_title = title[:20]
        title_selectors = ['input[placeholder*="填写标题"]', '.c-input_inner', 'input[type="text"]']
        for sel in title_selectors:
            loc = page.locator(sel).first
            if loc.count() > 0 and loc.is_visible():
                try:
                    loc.click()
                    loc.fill(short_title)
                    print(f">> 标题已填入: {short_title}")
                    break
                except Exception:
                    continue

        # 3. 填写正文与话题标签
        print(">> 正在填写正文描述与话题标签...")
        body_text = f"{title}\n\n{tags}"
        desc_selectors = ['#post-textarea', 'div[contenteditable="true"]', 'textarea']
        for sel in desc_selectors:
            loc = page.locator(sel).first
            if loc.count() > 0 and loc.is_visible():
                try:
                    loc.click()
                    page.keyboard.type(body_text, delay=20)
                    print(">> 正文与话题已填入！")
                    break
                except Exception:
                    continue

        # 4. 发布
        if auto_click:
            print(">> 正在定位小红书【发布】按钮...")
            time.sleep(5)
            pub_btn = page.locator('button:has-text("发布")').first
            if pub_btn.count() > 0:
                try:
                    pub_btn.scroll_into_view_if_needed()
                    pub_btn.click(timeout=10000)
                    print("\n[√] 小红书笔记已成功自动点击【发布】！")
                    time.sleep(3)
                except Exception as e:
                    print(f"[!] 点击发布遇到提示阻碍 ({e})，请在浏览器中核对后手动确认。")
            else:
                print("[!] 未找到发布按钮，请在浏览器中确认点击。")
        else:
            print("\n[提示] 小红书内容已填好，请在浏览器中检查后手动点击发布。")
            input(">> 确认发布后，请按回车继续... ")

    except Exception as e:
        print(f"\n[错误] 小红书发布过程中出现异常: {e}")
    finally:
        time.sleep(2)
        context.close()
        print(">> 小红书发布任务执行完毕，浏览器已安全退出。")

def publish_weixin(p, video_path, title, tags, auto_click=True):
    """微信视频号助手自动发布"""
    print("\n--------------------------------------------------------")
    print("▶ [3/3] 正在启动【微信视频号】发布流程...")
    print("--------------------------------------------------------")
    context, page = get_browser_context(p, "weixin")
    try:
        url = "https://channels.weixin.qq.com/platform/post/create"
        print(f">> 正在打开微信视频号发表页: {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        time.sleep(3)

        # 检查登录
        if "login" in page.url or page.locator('text="扫码登录"').count() > 0:
            print("\n[!] 提示：检测到当前微信视频号尚未登录！")
            input(">> 请使用微信扫码登录视频号助手，完成后回到此处按回车 [Enter] 继续: ")

        # 1. 上传视频
        print(">> 正在自动上传视频文件...")
        try:
            file_input = page.wait_for_selector('input[type="file"]', timeout=15000)
            file_input.set_input_files(video_path)
            print(">> 视频文件已填入视频号上传组件，正在解析处理...")
        except Exception as e:
            print(f"[!] 尝试备用定位上传: {e}")
            page.set_input_files('input[type="file"]', video_path)

        time.sleep(5)

        # 2. 填写动态描述
        print(">> 正在自动填写动态描述与话题标签...")
        post_text = f"{title} {tags}"
        desc_selectors = ['div[contenteditable="true"]', '.post-description', 'textarea']
        for sel in desc_selectors:
            loc = page.locator(sel).first
            if loc.count() > 0 and loc.is_visible():
                try:
                    loc.click()
                    page.keyboard.type(post_text, delay=20)
                    print(">> 动态描述已成功填入！")
                    break
                except Exception:
                    continue

        # 3. 发表
        if auto_click:
            print(">> 正在定位【发表】按钮...")
            time.sleep(5)
            pub_btn = page.locator('button:has-text("发表"), button:has-text("发布")').first
            if pub_btn.count() > 0:
                try:
                    pub_btn.scroll_into_view_if_needed()
                    pub_btn.click(timeout=10000)
                    print("\n[√] 微信视频号已成功自动点击【发表】！")
                    time.sleep(3)
                except Exception as e:
                    print(f"[!] 自动点击发表遇到提示阻碍 ({e})，请在浏览器中核对后手动确认。")
            else:
                print("[!] 未找到发表按钮，请在浏览器中核对后手动点击。")
        else:
            print("\n[提示] 视频号内容已填好，请在浏览器中检查后手动点击发表。")
            input(">> 确认发表后，请按回车继续... ")

    except Exception as e:
        print(f"\n[错误] 微信视频号发布过程中出现异常: {e}")
    finally:
        time.sleep(2)
        context.close()
        print(">> 微信视频号发布任务执行完毕，浏览器已安全退出。")

def main():
    print("========================================================")
    print("       🚀 自媒体多平台全自动发布工具 v1.0")
    print("========================================================")

    # 1. 加载文件与配置
    video_path, title, tags = load_video_and_meta()
    video_size_mb = os.path.getsize(video_path) / (1024 * 1024)

    print(f">> 视频文件: 【{os.path.basename(video_path)}】 ({video_size_mb:.2f} MB)")
    print(f">> 视频标题: \"{title}\"")
    print(f">> 话题标签: \"{tags}\"")
    print("========================================================")

    # 2. 选择发布模式
    print("请选择目标发布平台：")
    print("  [1] 抖音创作者中心")
    print("  [2] 小红书创作服务平台")
    print("  [3] 微信视频号助手")
    print("  [4] 全平台自动一键连发 (依次自动发布以上三平台) - 默认")
    print("--------------------------------------------------------")

    try:
        platform_choice = input(">> 请输入平台序号 [1-4] (直接回车默认选 4 全部): ").strip()
    except (EOFError, KeyboardInterrupt):
        platform_choice = "4"

    if not platform_choice:
        platform_choice = "4"

    with sync_playwright() as p:
        if platform_choice == "1":
            publish_douyin(p, video_path, title, tags, auto_click=True)
        elif platform_choice == "2":
            publish_xiaohongshu(p, video_path, title, tags, auto_click=True)
        elif platform_choice == "3":
            publish_weixin(p, video_path, title, tags, auto_click=True)
        elif platform_choice == "4":
            print("\n>>> 开始执行全平台一键连发模式...")
            publish_douyin(p, video_path, title, tags, auto_click=True)
            publish_xiaohongshu(p, video_path, title, tags, auto_click=True)
            publish_weixin(p, video_path, title, tags, auto_click=True)
        else:
            print("[错误] 无效的选项！")
            return

    print("\n========================================================")
    print("   🎉 自动化发布任务全部执行完毕！")
    print("========================================================\n")

if __name__ == "__main__":
    main()
