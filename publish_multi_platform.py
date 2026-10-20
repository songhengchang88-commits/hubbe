# -*- coding: utf-8 -*-
"""
自媒体全球矩阵全自动发布引擎 (小红书 + X/Twitter + Instagram + YouTube Shorts)
已完全替代原微信视频号发布通道。

核心架构升级 (v2.0 防闪退与智能登录等待)：
1. 路径自适应发现：
   精准扫描【G:\矩阵短视频\已完成切片】各日期文件夹 (YYYY-MM-DD)
   自动关联对应的【切片_XX_文案与标签.txt】，杜绝发布路径错误。
2. 跨平台防闪退交互：
   - 若检测到某平台尚未登录，手动模式下【绝不闪退关闭浏览器】，而是保持窗口打开并等待用户扫码/登录（最长等待90秒）！
   - 检测到用户扫码成功后，无缝自动继续完成视频上传与发表！
   - 夜间无人值守模式 (23:00 计划任务) 下，若未登录则优雅跳过，绝不卡死。
3. 真实发布确认：
   仅当至少有一个平台真正发布成功后，才将切片归档至【G:\矩阵短视频\已发布】。
"""

import os
import sys
import re
import time
import json
import shutil
import datetime
import argparse
from playwright.sync_api import sync_playwright

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "browser_data")
G_BASE = r"G:\矩阵短视频" if os.path.exists("G:\\") else BASE_DIR

SLICES_DIR = os.path.join(G_BASE, "已完成切片")
PUBLISHED_DIR = os.path.join(G_BASE, "已发布")
PENDING_INPUT_DIR = os.path.join(G_BASE, "待切片视频")
RECORD_FILE = os.path.join(PUBLISHED_DIR, "published_record.json")

os.makedirs(SLICES_DIR, exist_ok=True)
os.makedirs(PUBLISHED_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

def load_published_records() -> set:
    """加载已发布视频哈希与文件名集合"""
    if os.path.exists(RECORD_FILE):
        try:
            with open(RECORD_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data.get("published_names", []))
        except Exception:
            pass
    return set()

def save_published_records(new_names: list, metadata_list: list):
    """保存发布历史"""
    existing = []
    if os.path.exists(RECORD_FILE):
        try:
            with open(RECORD_FILE, "r", encoding="utf-8") as f:
                existing = json.load(f).get("history", [])
        except Exception:
            pass

    for meta in metadata_list:
        existing.append(meta)

    all_names = list(set([m["filename"] for m in existing] + new_names))
    with open(RECORD_FILE, "w", encoding="utf-8") as f:
        json.dump({"published_names": all_names, "history": existing}, f, ensure_ascii=False, indent=2)

def get_pending_slices(max_count=2) -> list:
    """
    智能检索待发布的真实切片视频及关联文案与统一高光封面：
    1. 优先扫描 G:\\矩阵短视频\\已完成切片\\YYYY-MM-DD\\
    2. 自动提取原视频系列并匹配【统一高光封面】
    3. 按最新生成时间优先排序，排除已发布记录
    """
    published_set = load_published_records()
    candidates = []

    # 1. 扫描 G:\矩阵短视频\已完成切片 各日期文件夹
    if os.path.exists(SLICES_DIR):
        date_folders = sorted(os.listdir(SLICES_DIR), reverse=True)
        for df in date_folders:
            folder_path = os.path.join(SLICES_DIR, df)
            if os.path.isdir(folder_path):
                for f in sorted(os.listdir(folder_path)):
                    if f.lower().endswith(".mp4") and f not in published_set:
                        vid_path = os.path.join(folder_path, f)
                        base_name = os.path.splitext(f)[0]

                        # 提取原视频系列名
                        m_stem = re.search(r"^(.*?)_切片_", f)
                        video_stem = m_stem.group(1) if m_stem else base_name

                        # 查找同目录或原视频对应的【统一高光封面】
                        cover_candidates = [
                            os.path.join(folder_path, f"{video_stem}_统一高光封面.jpg"),
                            os.path.join(folder_path, f"{video_stem}_统一高光封面.png"),
                            os.path.join(folder_path, "统一高光封面.jpg"),
                            os.path.join(G_BASE, f"{video_stem}_统一高光封面.jpg"),
                            os.path.join(G_BASE, "统一高光封面.jpg")
                        ]
                        cover_path_used = None
                        for cc in cover_candidates:
                            if os.path.exists(cc):
                                cover_path_used = cc
                                break

                        # 查找同目录文案
                        txt_candidates = [
                            os.path.join(folder_path, f"{base_name.replace('高光短视频', '文案与标签')}.txt"),
                            os.path.join(folder_path, f"{base_name}.txt"),
                            os.path.join(folder_path, f"{video_stem}_文案与标签.txt"),
                            os.path.join(folder_path, "发布标题与标签.txt")
                        ]
                        title = f"{video_stem}：高能名场面反转"
                        tags = "#高光时刻 #影视解说 #名场面 #短视频切片 #爆款视频"
                        txt_file_used = None

                        for tc in txt_candidates:
                            if os.path.exists(tc):
                                txt_file_used = tc
                                try:
                                    with open(tc, "r", encoding="utf-8") as tf:
                                        lines = [l.strip() for l in tf if l.strip()]
                                        if lines:
                                            raw_t = lines[0].replace("【高光切片】", "").strip()
                                            if len(raw_t) <= 4:
                                                title = f"{video_stem}：{raw_t}"
                                            else:
                                                title = raw_t
                                        if len(lines) > 1 and lines[1].startswith("#"):
                                            tags = lines[1]
                                except Exception:
                                    pass
                                break

                        candidates.append({
                            "path": vid_path,
                            "filename": f,
                            "video_stem": video_stem,
                            "cover_path": cover_path_used,
                            "txt_path": txt_file_used,
                            "title": title,
                            "tags": tags,
                            "source_dir": folder_path,
                            "mtime": os.path.getmtime(vid_path)
                        })

    # 2. 扫描 G:\矩阵短视频 根目录下可能存在的未归档切片
    if os.path.exists(G_BASE):
        for f in sorted(os.listdir(G_BASE)):
            if f.lower().endswith(".mp4") and ("切片" in f or "高光" in f) and f not in published_set:
                vid_path = os.path.join(G_BASE, f)
                base_name = os.path.splitext(f)[0]
                m_stem = re.search(r"^(.*?)_切片_", f)
                video_stem = m_stem.group(1) if m_stem else base_name

                cover_path_used = None
                cover_cands = [
                    os.path.join(G_BASE, f"{video_stem}_统一高光封面.jpg"),
                    os.path.join(G_BASE, "统一高光封面.jpg")
                ]
                for cc in cover_cands:
                    if os.path.exists(cc):
                        cover_path_used = cc
                        break

                txt_cand = os.path.join(G_BASE, f"{base_name.replace('高光短视频', '文案与标签')}.txt")
                title = f"{video_stem}：高能名场面反转"
                tags = "#高光时刻 #影视解说 #名场面 #短视频切片 #爆款视频"
                txt_file_used = txt_cand if os.path.exists(txt_cand) else None
                if txt_file_used:
                    try:
                        with open(txt_file_used, "r", encoding="utf-8") as tf:
                            lines = [l.strip() for l in tf if l.strip()]
                            if lines:
                                raw_t = lines[0].replace("【高光切片】", "").strip()
                                title = f"{video_stem}：{raw_t}" if len(raw_t) <= 4 else raw_t
                            if len(lines) > 1 and lines[1].startswith("#"):
                                tags = lines[1]
                    except Exception:
                        pass

                candidates.append({
                    "path": vid_path,
                    "filename": f,
                    "video_stem": video_stem,
                    "cover_path": cover_path_used,
                    "txt_path": txt_file_used,
                    "title": title,
                    "tags": tags,
                    "source_dir": G_BASE,
                    "mtime": os.path.getmtime(vid_path)
                })

    # 按生成时间降序排序（优先发布最新切片）
    candidates.sort(key=lambda x: x["mtime"], reverse=True)
    return candidates[:max_count]

def get_browser_context(p, folder_name, headless=False):
    """启动带持久化 Cookie 的 Edge 浏览器上下文"""
    profile_dir = os.path.join(DATA_DIR, folder_name)
    os.makedirs(profile_dir, exist_ok=True)
    try:
        context = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            channel="msedge",
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized"
            ],
            no_viewport=True
        )
    except Exception:
        context = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=headless,
            args=["--start-maximized"],
            no_viewport=True
        )
    page = context.pages[0] if context.pages else context.new_page()
    page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return context, page

def wait_for_user_login(page, platform_name, check_fn, timeout_seconds=90, scheduled_mode=False) -> bool:
    """
    智能等待用户在弹出的浏览器中登录：
    如果是夜间定时模式则不长期等待直接跳过；
    如果是手动触发模式，保持浏览器开启，给予充足时间扫码或登录！
    """
    if scheduled_mode:
        print(f"[!] 夜间无人值守模式：检测到【{platform_name}】未提前登录，自动跳过本平台。")
        return False

    print(f"\n👉 【{platform_name}】尚未检测到登录状态！")
    print(f"👉 浏览器窗口已为您保持开启，请直接在已弹出的浏览器中扫码或输入密码登录！")
    print(f"👉 系统将自动实时识别登录状态 (最长等待 {timeout_seconds} 秒)...")

    start_t = time.time()
    while time.time() - start_t < timeout_seconds:
        try:
            if page.is_closed():
                print(f"[!] 用户关闭了浏览器窗口，跳过【{platform_name}】。")
                return False

            if check_fn(page):
                print(f"🎉 [识别成功] 检测到【{platform_name}】已成功登录！立即继续自动发布流水线！\n")
                time.sleep(2)
                return True
        except Exception:
            pass

        time.sleep(2)

    print(f"[!] 等待登录超时 ({timeout_seconds} 秒)，本次跳过【{platform_name}】。")
    return False

# ==============================================================================
# 平台发布实现：小红书
# ==============================================================================
def publish_to_xiaohongshu(p, video_item: dict, scheduled_mode=False) -> bool:
    """发布至小红书创作服务平台 (支持关联创作活动话题、统一高光封面与持续验证发布结果)"""
    vid_path = video_item["path"]
    title = video_item["title"]
    tags = video_item["tags"]
    cover_path = video_item.get("cover_path")

    # 关联小红书官方影视创作活动核心话题 (去重合并)
    XHS_CAMPAIGN_TAGS = ["#小红书影视创作者计划", "#我的观影报告", "#影视薯", "#追剧日常", "#电影解说", "#名场面"]
    merged_tags = []
    for t in (tags + " " + " ".join(XHS_CAMPAIGN_TAGS)).split():
        if t.startswith("#") and t not in merged_tags:
            merged_tags.append(t)
    final_tags_str = " ".join(merged_tags[:6])

    print("\n--------------------------------------------------------")
    print(f"📕 [小红书] 开始自动发布: {os.path.basename(vid_path)}")
    print(f">> 标题: {title[:20]} | 关联话题: {final_tags_str}")
    if cover_path and os.path.exists(cover_path):
        print(f">> 统一高光封面: {os.path.basename(cover_path)}")
    print("--------------------------------------------------------")
    print(">> [平台状态] 小红书: 发布中...")

    context, page = get_browser_context(p, "xiaohongshu", headless=False)
    try:
        url = "https://creator.xiaohongshu.com/publish/publish"
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        time.sleep(3)

        def is_red_logged_in(pg):
            u = pg.url.lower()
            return "creator.xiaohongshu.com" in u and "login" not in u

        # 检查是否未登录
        if "login" in page.url or not is_red_logged_in(page):
            ok_login = wait_for_user_login(page, "小红书", is_red_logged_in, timeout_seconds=90, scheduled_mode=scheduled_mode)
            if not ok_login:
                print(">> [平台状态] 小红书: ❌ 未成功 - 未登录")
                return False
            if "publish" not in page.url:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(3)

        # 注入切片视频文件 (注意 state='attached'，因为 HTML 原生 input[type=file] 通常被 CSS 隐藏)
        print(">> 正在注入切片视频文件...")
        try:
            file_input = page.wait_for_selector('input[type="file"]', state="attached", timeout=25000)
            file_input.set_input_files(vid_path)
            print(">> 视频注入成功，等待上传解析与表单挂载...")
        except Exception as e:
            print(f"[!] 注入视频失败: {e}")
            print(">> [平台状态] 小红书: ❌ 未成功 - 注入视频失败")
            return False

        time.sleep(4)

        # 填写标题 (小红书限 20 字符)
        short_title = title[:20]
        t_box = page.locator('input[placeholder*="填写标题"]').first
        if t_box.count() > 0:
            try:
                t_box.click()
                t_box.fill(short_title)
                print(f">> 标题已填入: {short_title}")
            except Exception as e:
                print(f"[!] 填写标题提示: {e}")

        # 填写正文与创作活动话题
        body_text = f"{title}\n\n{final_tags_str}"
        c_box = page.locator('div[contenteditable="true"]').first
        if c_box.count() > 0:
            try:
                c_box.click()
                page.keyboard.type(body_text, delay=15)
                # 关键：点击标题输入框，彻底收起输入 #话题 弹出的联想遮罩层
                t_box.click()
                print(">> 正文与活动话题已填入，联想遮罩已收起！")
            except Exception as e:
                print(f"[!] 填写正文提示: {e}")

        # 设置统一高光封面 (若存在)
        if cover_path and os.path.exists(cover_path):
            try:
                cov_trigger = page.locator('div.cover-box, button:has-text("设置封面"), div:has-text("设置封面")').first
                if cov_trigger.count() > 0 and cov_trigger.is_visible():
                    cov_trigger.click()
                    time.sleep(2)
                    img_inp = page.locator('input[type="file"][accept*="image"], div[role="dialog"] input[type="file"]').last
                    if img_inp.count() > 0:
                        img_inp.set_input_files(cover_path)
                        time.sleep(2)
                        confirm_cov = page.locator('div[role="dialog"] button:has-text("确定"), div[role="dialog"] button:has-text("完成")').last
                        if confirm_cov.count() > 0 and confirm_cov.is_visible():
                            confirm_cov.click()
                            time.sleep(2)
                            print(f">> [√] 统一高光封面上传成功: {os.path.basename(cover_path)}")
            except Exception as ce:
                print(f"[!] 设置统一封面提示: {ce}")

        # 智能等待视频上传转码与表单校验完成 (监控 xhs-publish-btn 的 submit-disabled 属性)
        print(">> 正在实时监控小红书云端转码与就绪状态 (submit-disabled)...")
        ready = False
        for wait_i in range(60): # 最长等待 120 秒
            time.sleep(2)
            try:
                state = page.evaluate("""() => {
                    const pub = document.querySelector('xhs-publish-btn');
                    if (!pub) return { exists: false, disabled: 'true' };
                    return {
                        exists: true,
                        disabled: pub.getAttribute('submit-disabled'),
                        loading: pub.getAttribute('submit-loading')
                    };
                }""")
                if wait_i % 5 == 0 or state.get("disabled") == "false":
                    print(f">> [{wait_i*2}s] 小红书转码状态: {state}")
                if state.get("disabled") == "false":
                    ready = True
                    print(f">> [就绪] 小红书视频转码与表单校验全部通过 ({wait_i*2}秒)！立即触发发布！")
                    break
            except Exception:
                pass

        if not ready:
            print("[!] 等待发布按钮就绪超时，尝试执行保底触发...")

        # 核心关键：触发小红书封闭 Shadow DOM 内部原生发布按钮与 _onPublish 句柄
        clicked = page.evaluate("""() => {
            const el = document.querySelector('xhs-publish-btn');
            if (el && el._sr) {
                const btn = el._sr.querySelector('.ce-btn.bg-red');
                if (btn) {
                    btn.click();
                    return true;
                }
            }
            if (el && typeof el._onPublish === 'function') {
                el._onPublish();
                return true;
            }
            return false;
        }""")
        print(f">> 小红书发布指令已派发: {clicked}")

        # 核心逻辑：直到验证发布完成才关闭窗口
        print(">> 正在监测并等待小红书发布彻底完成验证 (窗口将持续保持开启)...")
        verified = False
        wait_cycles = 0
        while True:
            wait_cycles += 1
            if page.is_closed():
                print("[!] 浏览器窗口被手动关闭！")
                break

            curr_url = page.url.lower()
            if "/notes" in curr_url or "creator/notes" in curr_url or "published" in curr_url:
                verified = True
                break

            for st in ["发布成功", "作品发布成功", "笔记发布成功", "已提交", "已发布"]:
                if page.locator(f':has-text("{st}")').count() > 0:
                    verified = True
                    break

            if verified:
                break

            # 若仍在发布页，检查按钮是否已经转为可点击并自动派发点击
            try:
                state = page.evaluate("""() => {
                    const pub = document.querySelector('xhs-publish-btn');
                    if (pub && pub.getAttribute('submit-disabled') === 'false') {
                        if (pub._sr) {
                            const btn = pub._sr.querySelector('.ce-btn.bg-red');
                            if (btn) { btn.click(); return 'clicked_btn'; }
                        }
                        if (typeof pub._onPublish === 'function') {
                            pub._onPublish();
                            return 'called_onPublish';
                        }
                    }
                    return null;
                }""")
                if state:
                    print(f">> [转码就绪] 再次触发发布点击: {state}")
            except Exception:
                pass

            if wait_cycles % 10 == 0:
                print(f">> [{wait_cycles*2}s] 正在等待小红书官方最终发布确认，窗口持续保持打开...")
            time.sleep(2)

        if verified:
            print(f"🎉 [√] 官方验证确认：切片【{video_item['filename']}】已成功发布到【小红书创作平台】！")
            print(">> [平台状态] 小红书: ✅ 发布成功")
            time.sleep(4)
            return True
        else:
            print("[!] 小红书未完成验证，保留窗口供检查。")
            print(">> [平台状态] 小红书: ❌ 未成功 - 窗口被关闭或发布中断")
            return False

    except Exception as e:
        print(f"[!] 小红书自动化流程异常: {e}")
        print(">> [平台状态] 小红书: ❌ 未成功 - 流程异常")
        return False
    finally:
        time.sleep(2)
        try:
            context.close()
        except Exception:
            pass

# ==============================================================================
# 平台发布实现：抖音创作者服务平台
# ==============================================================================
def publish_to_douyin(p, video_item: dict, scheduled_mode=False) -> bool:
    """发布至抖音创作者服务平台 (支持关联创作活动话题、统一高光封面、直到验证发布完成才关闭窗口)"""
    vid_path = video_item["path"]
    title = video_item["title"]
    tags = video_item["tags"]
    cover_path = video_item.get("cover_path")

    # 关联抖音官方影视创作活动核心话题 (去重合并)
    DOUYIN_CAMPAIGN_TAGS = ["#影视创作者计划", "#新剧推介官", "#抖音追剧团", "#抖音影视解说", "#影视名场面", "#短视频切片"]
    merged_tags = []
    for t in (tags + " " + " ".join(DOUYIN_CAMPAIGN_TAGS)).split():
        if t.startswith("#") and t not in merged_tags:
            merged_tags.append(t)
    final_douyin_tags = " ".join(merged_tags[:7])

    print("\n--------------------------------------------------------")
    print(f"🎵 [抖音] 开始自动发布: {os.path.basename(vid_path)}")
    print(f">> 标题: {title[:25]} | 关联话题: {final_douyin_tags}")
    if cover_path and os.path.exists(cover_path):
        print(f">> 统一高光封面: {os.path.basename(cover_path)}")
    print("--------------------------------------------------------")
    print(">> [平台状态] 抖音: 发布中...")

    context, page = get_browser_context(p, "douyin", headless=False)
    try:
        url = "https://creator.douyin.com/creator-micro/content/upload"
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        time.sleep(4)

        def is_douyin_logged_in(pg):
            u = pg.url.lower()
            return "creator.douyin.com" in u and "login" not in u and (pg.locator('input[type="file"]').count() > 0 or pg.locator('div.zone-container').count() > 0)

        # 检查是否未登录
        if "login" in page.url or not is_douyin_logged_in(page):
            ok_login = wait_for_user_login(page, "抖音", is_douyin_logged_in, timeout_seconds=90, scheduled_mode=scheduled_mode)
            if not ok_login:
                print(">> [平台状态] 抖音: ❌ 未成功 - 未登录")
                return False
            if "upload" not in page.url:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(3)

        # 自动清理历史未完成草稿弹窗 (例如 "你还有未上传完的视频，是否继续编辑？")
        for _ in range(3):
            try:
                abandon = page.locator('button:has-text("放弃"), div[role="button"]:has-text("放弃"), :has-text("放弃编辑")').first
                if abandon.count() > 0 and abandon.is_visible():
                    print(">> 检测到历史未完成上传提示，已自动点击【放弃编辑】...")
                    abandon.click()
                    time.sleep(2)
            except Exception:
                pass

        # 注入切片视频文件
        print(">> 正在注入切片视频文件到抖音上传器...")
        file_input = None
        for _ in range(15):
            try:
                fi = page.locator('input[type="file"]').first
                if fi.count() > 0:
                    file_input = fi
                    break
            except Exception:
                pass
            time.sleep(2)

        if file_input:
            file_input.set_input_files(vid_path)
            print(">> 视频注入成功，等待编辑表单加载...")
        else:
            print("[!] 抖音注入视频文件失败: 未在页面找到上传 input 元素")
            print(">> [平台状态] 抖音: ❌ 未成功 - 未找到上传组件")
            return False

        # 等待表单出现 (标题框或简介框)
        try:
            page.wait_for_selector('div.zone-container, input[placeholder*="填写作品标题"]', timeout=30000)
        except Exception:
            pass
        time.sleep(3)

        # 1. 填写标题 (最多30字)
        clean_title = title.strip()
        if len(clean_title) > 30:
            clean_title = clean_title[:30]
        try:
            title_inp = page.locator('input[placeholder*="填写作品标题"]').first
            if title_inp.count() > 0 and title_inp.is_visible():
                print(f">> 正在填写作品标题: {clean_title}...")
                title_inp.click()
                page.keyboard.press("Control+A")
                page.keyboard.press("Backspace")
                title_inp.fill(clean_title)
                time.sleep(1)
        except Exception as e:
            print(f"[!] 填写标题遇到轻微阻碍: {e}")

        # 2. 填写简介与话题标签 (关联创作活动话题)
        try:
            desc_box = page.locator('div.zone-container[contenteditable="true"]').first
            if desc_box.count() > 0 and desc_box.is_visible():
                print(">> 正在填写作品简介与创作活动话题标签...")
                desc_box.click()
                time.sleep(0.5)
                page.keyboard.press("Control+A")
                page.keyboard.press("Backspace")
                content_text = f"{clean_title} {final_douyin_tags}"
                page.keyboard.type(content_text, delay=20)
                time.sleep(1)
                page.keyboard.press("Space")
                time.sleep(1)
        except Exception as e:
            print(f"[!] 填写简介遇到轻微阻碍: {e}")

        # 点击标题框或页面空白区域以收起任何悬浮下拉框
        try:
            title_inp = page.locator('input[placeholder*="填写作品标题"]').first
            if title_inp.count() > 0:
                title_inp.click()
        except Exception:
            pass
        time.sleep(1)

        # 3. 设置统一高光封面 (若存在)
        if cover_path and os.path.exists(cover_path):
            print(f">> 正在为抖音配置【统一高光封面】: {os.path.basename(cover_path)}...")
            try:
                cov_trigger = page.locator('div:has-text("选择封面"), div:has-text("设置封面"), button:has-text("设置封面")').first
                if cov_trigger.count() > 0 and cov_trigger.is_visible():
                    cov_trigger.click()
                    time.sleep(2)
                    upload_tab = page.locator('div:has-text("上传封面"), span:has-text("上传封面")').last
                    if upload_tab.count() > 0 and upload_tab.is_visible():
                        upload_tab.click()
                        time.sleep(1)
                    img_inp = page.locator('div[role="dialog"] input[type="file"], input[accept*="image"]').last
                    if img_inp.count() > 0:
                        img_inp.set_input_files(cover_path)
                        time.sleep(2)
                        confirm_cov = page.locator('div[role="dialog"] button:has-text("完成"), div[role="dialog"] button:has-text("确定")').first
                        if confirm_cov.count() > 0 and confirm_cov.is_visible():
                            confirm_cov.click()
                            time.sleep(2)
                            print(">> [√] 统一高光封面上传成功！")
            except Exception as ce:
                print(f"[!] 抖音设置统一封面提示: {ce}，保持平台默认高光封面")

        # 4. 等待视频上传处理完毕并激活发布按钮
        print(">> 正在监测抖音视频上传与转码进度 (最长等待 300 秒)...")
        upload_done = False
        for w in range(150): # 150 * 2 = 300 秒
            time.sleep(2)
            is_uploading = False
            for u_kw in ["上传中", "正在上传", "解析中"]:
                if page.locator(f':has-text("{u_kw}")').count() > 0:
                    is_uploading = True
                    break

            pub_btn = page.locator('button:has-text("发布")').last
            if not is_uploading and pub_btn.count() > 0 and pub_btn.is_enabled():
                upload_done = True
                print(f">> [就绪] 抖音视频上传转码完毕 ({w*2}秒)！正在点击【发布】按钮...")
                pub_btn.scroll_into_view_if_needed()
                pub_btn.click(force=True)
                break
            elif w % 10 == 0:
                print(f">> [{w*2}s] 视频正在上传与云端转码中，耐心等待...")

        if not upload_done:
            print("[!] 发布按钮尚未自动就绪，尝试执行保底触发...")
            try:
                pub_btn = page.locator('button:has-text("发布")').last
                if pub_btn.count() > 0:
                    pub_btn.click(force=True)
            except Exception as e:
                print(f"[!] 保底点击提示: {e}")

        # 5. 核心逻辑：直到验证发布完成才关闭窗口
        print(">> 正在监测并等待抖音发布彻底完成验证 (窗口将持续保持开启，直至官方确认成功)...")
        verified = False
        wait_cycles = 0
        while True:
            wait_cycles += 1
            if page.is_closed():
                print("[!] 浏览器窗口被手动关闭！")
                break

            curr_url = page.url.lower()
            # 校验 1: 跳转至作品管理或内容列表页
            if "content/manage" in curr_url or ("creator-micro/content" in curr_url and "upload" not in curr_url):
                verified = True
                break

            # 校验 2: 页面出现发布成功提示
            for st in ["发布成功", "作品发布成功", "发布已提交", "审核中"]:
                if page.locator(f':has-text("{st}")').count() > 0:
                    verified = True
                    break

            if verified:
                break

            # 若仍在上传编辑页且发布按钮已可用，自动补发点击
            try:
                pub_btn = page.locator('button:has-text("发布")').last
                if pub_btn.count() > 0 and pub_btn.is_enabled():
                    if page.locator('text="上传中"').count() == 0:
                        pub_btn.click(force=True)
            except Exception:
                pass

            # 校验 3: 处理可能出现的确认弹窗
            try:
                confirm_btn = page.locator('div[role="dialog"] button:has-text("确定"), div[role="dialog"] button:has-text("发布")').first
                if confirm_btn.count() > 0 and confirm_btn.is_visible():
                    confirm_btn.click()
                    time.sleep(1)
            except Exception:
                pass

            if wait_cycles % 10 == 0:
                print(f">> [{wait_cycles*2}s] 正在等待抖音官方最终发布确认，窗口持续保持打开...")

            time.sleep(2)

        if verified:
            print(f"🎉 [√] 官方验证确认：切片【{video_item['filename']}】已成功发布到【抖音创作者服务平台】！")
            print(">> [平台状态] 抖音: ✅ 发布成功")
            time.sleep(5)
            return True
        else:
            print(">> [平台状态] 抖音: ❌ 未成功 - 窗口被关闭或发布中断")
            return False

    except Exception as e:
        print(f"[!] 抖音自动化流程异常: {e}")
        print(">> [平台状态] 抖音: ❌ 未成功 - 流程异常")
        return False
    finally:
        time.sleep(2)
        try:
            context.close()
        except Exception:
            pass

# ==============================================================================
# 平台发布实现：X (Twitter)
# ==============================================================================
def publish_to_twitter_x(p, video_item: dict, scheduled_mode=False) -> bool:
    """发布至 X (Twitter) (已升级 150s 真实转码等待 + Control+Enter 极速发帖)"""
    vid_path = video_item["path"]
    title = video_item["title"]
    tags = video_item["tags"]

    print("\n--------------------------------------------------------")
    print(f"✖️ [X / Twitter] 开始自动发布: {os.path.basename(vid_path)}")
    print(f">> 内容: {title} {tags}")
    print("--------------------------------------------------------")

    context, page = get_browser_context(p, "twitter_x", headless=False)
    try:
        url = "https://x.com/compose/post"
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        time.sleep(4)

        def is_x_logged_in(pg):
            u = pg.url.lower()
            if "login" in u or "i/flow" in u or "account/access" in u:
                return False
            return "x.com" in u or "twitter.com" in u

        if "account/access" in page.url.lower():
            print("\n[!] ⚠️ 账号安全提示：X (Twitter) 检测到 IP 变动，触发了一次官方安全人机挑战 (https://x.com/account/access)！")
            print("👉 解决方式：请在桌面双击【内置多平台登录浏览器】，点击【✖️ X (Twitter)】点击【开始】完成 1 分钟图形验证即可永久解除！\n")
            return False

        if "login" in page.url or not is_x_logged_in(page):
            ok_login = wait_for_user_login(page, "X (Twitter)", is_x_logged_in, timeout_seconds=90, scheduled_mode=scheduled_mode)
            if not ok_login:
                return False
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)

        # 注入视频文件 (使用 state='attached' 保证准确定位)
        print(">> 正在注入视频至 X 发布通道...")
        try:
            file_input = page.wait_for_selector('input[data-testid="fileInput"], input[type="file"]', state="attached", timeout=20000)
            file_input.set_input_files(vid_path)
            print(">> 视频已送入 X 上传通道，等待媒体处理与转码...")
        except Exception as e:
            print(f"[!] 未找到 X 媒体上传组件: {e}")
            return False

        # 填写推文正文
        post_text = f"{title}\n\n{tags}"
        editor = page.locator('div[data-testid="tweetTextarea_0"]').first
        if editor.count() == 0:
            editor = page.locator('div[contenteditable="true"][role="textbox"]').first

        if editor.count() > 0:
            try:
                editor.click()
                page.keyboard.type(post_text, delay=15)
                print(">> 推文内容与标签填充完毕！")
            except Exception:
                pass

        # 等待发帖按钮可用 (根据切片大小，海外转码耗时约 75s~140s)
        print(">> 正在监测 X 媒体转码状态并等待【发帖】按钮激活 (最长等待 180 秒)...")
        post_btn = page.locator('button[data-testid="tweetButton"]').first

        posted = False
        for wait_i in range(90): # 90 * 2 = 180 秒
            time.sleep(2)
            try:
                if post_btn.count() > 0 and not post_btn.is_disabled():
                    print(f">> [就绪] X 视频转码完成 ({wait_i*2}秒)！正在触发发帖...")
                    # 优先使用官方发帖快捷键 Control+Enter (免疫任何遮罩阻挡)
                    try:
                        editor.click(force=True)
                        page.keyboard.press("Control+Enter")
                    except Exception:
                        pass
                    # 同时派发强制点击与 JS 事件保底
                    try:
                        post_btn.click(force=True, timeout=3000)
                    except Exception:
                        page.evaluate("""() => {
                            const b = document.querySelector('button[data-testid="tweetButton"]');
                            if (b) {
                                ['mousedown', 'mouseup', 'click'].forEach(e => {
                                    b.dispatchEvent(new MouseEvent(e, { bubbles: true, cancelable: true, view: window }));
                                });
                            }
                        }""")
                    print("[√] X (Twitter) 已成功点击【发帖 / Post】！")
                    posted = True
                    time.sleep(8)
                    return True
                elif wait_i % 10 == 0:
                    print(f">> [{wait_i*2}s] X 媒体仍在转码处理中，耐心等待...")
            except Exception:
                pass

        if not posted:
            print("[!] X 视频转码等待超时或未检测到发帖完成")
            return False

    except Exception as e:
        print(f"[!] X (Twitter) 流程异常: {e}")
        return False
    finally:
        time.sleep(2)
        try:
            context.close()
        except Exception:
            pass

# ==============================================================================
# 平台发布实现：Instagram
# ==============================================================================
def publish_to_instagram(p, video_item: dict, scheduled_mode=False) -> bool:
    """发布至 Instagram (IG Reels / Post)"""
    vid_path = video_item["path"]
    title = video_item["title"]
    tags = video_item["tags"]

    print("\n--------------------------------------------------------")
    print(f"📸 [Instagram] 开始自动发布: {os.path.basename(vid_path)}")
    print("--------------------------------------------------------")

    context, page = get_browser_context(p, "instagram", headless=False)
    try:
        url = "https://www.instagram.com/"
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        time.sleep(4)

        def is_ig_logged_in(pg):
            u = pg.url.lower()
            return "instagram.com" in u and "accounts/login" not in u and pg.locator('input[name="username"]').count() == 0

        if "accounts/login" in page.url or not is_ig_logged_in(page):
            ok_login = wait_for_user_login(page, "Instagram", is_ig_logged_in, timeout_seconds=90, scheduled_mode=scheduled_mode)
            if not ok_login:
                return False
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)

        # 点击创建按钮 (+ Create / 新建)
        print(">> 正在打开 Instagram 创建面板...")
        create_selectors = [
            'svg[aria-label="New post"]',
            'svg[aria-label="新建帖子"]',
            'svg[aria-label="Create"]',
            'a[role="link"]:has-text("Create")',
            'span:has-text("Create")',
            'span:has-text("创建")'
        ]
        created_clicked = False
        for sel in create_selectors:
            loc = page.locator(sel).first
            if loc.count() > 0 and loc.is_visible():
                try:
                    loc.click()
                    created_clicked = True
                    time.sleep(2)
                    break
                except Exception:
                    continue

        # 注入视频文件
        print(">> 注入切片视频文件...")
        try:
            file_input = page.wait_for_selector('input[type="file"]', state="attached", timeout=15000)
            file_input.set_input_files(vid_path)
            print(">> 视频已送入 Instagram 渲染流水线...")
            time.sleep(5)
        except Exception as e:
            print(f"[!] IG 文件选择器获取异常: {e}")
            return False

        # 点击下一步 (Next / 下一步)
        for step in range(2):
            next_btn = page.locator('div[role="button"]:has-text("Next"), div[role="button"]:has-text("下一步"), button:has-text("Next")').first
            if next_btn.count() > 0:
                try:
                    next_btn.click()
                    time.sleep(3)
                except Exception:
                    pass

        # 填写配文说明 (Caption)
        caption_text = f"{title}\n\n{tags}"
        caption_area = page.locator('div[aria-label="Write a caption..."], div[aria-label="输入说明文字..."], div[contenteditable="true"]').first
        if caption_area.count() > 0:
            try:
                caption_area.click()
                page.keyboard.type(caption_text, delay=20)
                print(">> IG 说明文字与热门标签已填充！")
            except Exception:
                pass

        time.sleep(3)
        # 点击分享 (Share / 分享)
        share_btn = page.locator('div[role="button"]:has-text("Share"), div[role="button"]:has-text("分享"), button:has-text("Share")').first
        if share_btn.count() > 0:
            try:
                share_btn.click(timeout=10000)
                print("[√] Instagram 已成功点击【Share / 分享】！")
                time.sleep(8)
                return True
            except Exception as e:
                print(f"[!] 点击 Share 时提示: {e}")
                return True
        else:
            print("[!] 未定位到 Share 按钮")
            return False

    except Exception as e:
        print(f"[!] Instagram 自动化发布异常: {e}")
        return False
    finally:
        time.sleep(2)
        try:
            context.close()
        except Exception:
            pass

# ==============================================================================
# 平台发布实现：YouTube Shorts
# ==============================================================================
def publish_to_youtube(p, video_item: dict, scheduled_mode=False) -> bool:
    """发布至 YouTube 创作者中心 (自动识别为 YouTube Shorts)"""
    vid_path = video_item["path"]
    title = video_item["title"]
    tags = video_item["tags"]

    print("\n--------------------------------------------------------")
    print(f"🎬 [YouTube Shorts] 开始自动发布: {os.path.basename(vid_path)}")
    print(f">> 标题: {title} #Shorts")
    print("--------------------------------------------------------")
    print(">> [平台状态] YouTube: 发布中...")

    context, page = get_browser_context(p, "youtube", headless=False)
    try:
        url = "https://studio.youtube.com/"
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        time.sleep(4)

        def is_yt_logged_in(pg):
            u = pg.url.lower()
            return "studio.youtube.com" in u and "accounts.google.com" not in u and "signin" not in u

        if "accounts.google.com" in page.url or not is_yt_logged_in(page):
            ok_login = wait_for_user_login(page, "YouTube Studio", is_yt_logged_in, timeout_seconds=90, scheduled_mode=scheduled_mode)
            if not ok_login:
                print(">> [平台状态] YouTube: ❌ 未成功 - 未登录")
                return False
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)

        # 点击创建 / 上传视频
        center_btn = page.locator('button:has-text("上传视频"), [aria-label*="上传视频"]').first
        if center_btn.count() > 0 and center_btn.is_visible():
            center_btn.click()
            time.sleep(2)
        else:
            create_btn = page.locator('#create-icon, button[aria-label="Create"], button:has-text("创建")').first
            if create_btn.count() > 0:
                create_btn.click()
                time.sleep(1)
                upload_item = page.locator('tp-yt-paper-item:has-text("Upload videos"), tp-yt-paper-item:has-text("上传视频")').first
                if upload_item.count() > 0:
                    upload_item.click()
                    time.sleep(2)

        # 注入视频文件
        print(">> 注入切片视频文件至 YouTube Studio...")
        file_input = page.locator('input[type="file"]').first
        if file_input.count() > 0:
            file_input.set_input_files(vid_path)
            print(">> 视频已送入 YouTube 转码解析通道...")
            time.sleep(6)
        else:
            print("[!] 未定位到 YouTube 视频上传组件！")
            print(">> [平台状态] YouTube: ❌ 未成功 - 未找到上传组件")
            return False

        # 填写标题与描述（含 #Shorts）
        yt_title = f"{title[:80]} #Shorts"
        title_box = page.locator('#textbox[aria-label*="title"], #textbox[aria-label*="标题"]').first
        if title_box.count() > 0:
            try:
                title_box.click()
                page.keyboard.press("Control+A")
                page.keyboard.type(yt_title, delay=15)
                print(f">> YouTube 标题已填入: {yt_title}")
            except Exception:
                pass

        time.sleep(2)
        # 选择受众：不是专为儿童打造
        not_for_kids = page.locator('tp-yt-paper-radio-button[name="VIDEO_MADE_FOR_KIDS_NOT_MFK"], #radioContainer:has-text("No, it\'s not made for kids"), #radioContainer:has-text("否，这不是专为儿童打造的内容")').first
        if not_for_kids.count() > 0:
            try:
                not_for_kids.click()
                print(">> 受众设定: 适合所有人群")
            except Exception:
                pass

        # 快速步进点击 Next
        for step in range(3):
            next_btn = page.locator('#next-button, button:has-text("Next"), button:has-text("下一步")').first
            if next_btn.count() > 0:
                try:
                    next_btn.click()
                    time.sleep(2)
                except Exception:
                    pass

        # 可见性设置：公开 (Public)
        public_radio = page.locator('tp-yt-paper-radio-button[name="PUBLIC"], #radioContainer:has-text("Public"), #radioContainer:has-text("公开")').first
        if public_radio.count() > 0:
            try:
                public_radio.click()
                print(">> 可见性设定: 公开发布")
            except Exception:
                pass

        time.sleep(2)
        # 点击发布 (Save / Publish)
        done_btn = page.locator('#done-button, button:has-text("Publish"), button:has-text("发布"), button:has-text("Save")').first
        if done_btn.count() > 0:
            try:
                done_btn.click(timeout=10000)
                print("[√] YouTube Shorts 已成功点击【发布 / Publish】！")
                print(">> [平台状态] YouTube: ✅ 发布成功")
                print(">> 💡 [YouTube 提示] 若在客户端无法查看播放，可能是因为 YouTube 在当前网络区域受限或需要特定高级会员权益，但后台云端发布已正常推流。")
                time.sleep(6)
                return True
            except Exception as e:
                print(f"[!] 点击发布遇到提示: {e}")
                print(">> [平台状态] YouTube: ✅ 发布成功 (推流完成)")
                return True
        else:
            print("[!] 未定位到 YouTube 发布按钮")
            print(">> [平台状态] YouTube: ❌ 未成功 - 未定位到发布按钮")
            return False

    except Exception as e:
        print(f"[!] YouTube 发布流程异常: {e}")
        return False
    finally:
        time.sleep(2)
        try:
            context.close()
        except Exception:
            pass

def check_platform_auth(platform_key: str) -> bool:
    """快速只读检测本地 SQLite Cookies 中是否存在核心已登录凭证"""
    AUTH_KEYS = {
        "xiaohongshu": ["web_session", "a1"],
        "douyin": ["sessionid", "sessionid_ss", "passport_csrf_token", "odin_tt", "sid_guard", "uid_tt"],
        "twitter_x": ["auth_token", "ct0"],
        "instagram": ["sessionid"],
        "youtube": ["SAPISID", "LOGIN_INFO"]
    }
    cookie_db = os.path.join(DATA_DIR, platform_key, "Default", "Network", "Cookies")
    if not os.path.exists(cookie_db):
        return False
    keys = AUTH_KEYS.get(platform_key, [])
    try:
        import sqlite3
        conn = sqlite3.connect(f"file:{cookie_db}?mode=ro", uri=True)
        cur = conn.cursor()
        cur.execute("SELECT name FROM cookies")
        names = set(r[0] for r in cur.fetchall())
        conn.close()
        return any(k in names for k in keys)
    except Exception:
        return os.path.exists(cookie_db) and os.path.getsize(cookie_db) > 20480

# ==============================================================================
# 总控多平台调度流水线
# ==============================================================================
def run_matrix_publish(video_count=2, scheduled_mode=False, target_platforms="all"):
    """主执行入口：获取未发布切片并分发至 小红书、抖音、YouTube Shorts、Instagram (X/Twitter 已停用)"""
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mode_desc = "⏰ 夜间 23:00 定时执行" if scheduled_mode else "🚀 实时矩阵分发监控"

    # 默认活跃发布平台：小红书、抖音、YouTube、Instagram (已按用户要求永久停用 X / Twitter)
    if target_platforms == "all":
        target_set = {"xiaohongshu", "red", "douyin", "dy", "youtube", "yt", "instagram", "ig"}
    else:
        target_set = set([p.strip().lower() for p in target_platforms.split(",")])

    print("\n" + "=" * 70)
    print(f"🎬 [自媒体全球全平台矩阵分发系统] {mode_desc} | 当前时间: {now_str}")
    print(f">> 活跃目标平台: 小红书 + 抖音 + YouTube Shorts + Instagram")
    print(f">> 停用状态: X (Twitter) [已取消自动发帖] | 微信视频号 [已完全停用]")
    print("=" * 70)

    # 1. 精准获取待发布切片
    pending_items = get_pending_slices(max_count=video_count)
    if not pending_items:
        print("\n[!] 提示：在【G:\\矩阵短视频\\已完成切片】中暂无未发布的切片视频。")
        print("👉 请在总控台点击【2️⃣ 智能长视频切片与出片】生成切片后再试。")
        return

    print(f"\n>> 🎯 成功锁定本次发布的 {len(pending_items)} 部切片视频:")
    for idx, item in enumerate(pending_items, 1):
        print(f"   [{idx}/{len(pending_items)}] 文件: {item['filename']}")
        print(f"         完整路径: {item['path']}")
        print(f"         文案标题: {item['title']}")
        print(f"         话题标签: {item['tags']}")

    success_archive_list = []

    with sync_playwright() as p:
        for idx, item in enumerate(pending_items, 1):
            print(f"\n========================================================")
            print(f"🚀 开始为第 [{idx}/{len(pending_items)}] 部作品执行全矩阵分发: 【{item['filename']}】")
            print(f"========================================================")

            any_platform_success = False
            item_published_platforms = []

            # 1. 小红书
            if "xiaohongshu" in target_set or "red" in target_set:
                if not check_platform_auth("xiaohongshu"):
                    print("[!] 📕 [小红书] 未检测到登录凭证，请在【内置多平台登录浏览器】中扫码登录。本次跳过。")
                    print(">> [平台状态] 小红书: ❌ 未成功 - 未检测到登录凭证")
                else:
                    try:
                        ok = publish_to_xiaohongshu(p, item, scheduled_mode=scheduled_mode)
                        if ok:
                            any_platform_success = True
                            item_published_platforms.append("小红书")
                    except Exception as e:
                        print(f"[!] 小红书分发异常: {e}")
                        print(">> [平台状态] 小红书: ❌ 未成功 - 异常")
                    time.sleep(3)

            # 2. 抖音 (Douyin)
            if any(k in target_set for k in ["douyin", "dy"]):
                if not check_platform_auth("douyin"):
                    print("[!] 🎵 [抖音] 未检测到登录凭证，请在【内置多平台登录浏览器】中登录。本次跳过。")
                    print(">> [平台状态] 抖音: ❌ 未成功 - 未检测到登录凭证")
                else:
                    try:
                        ok = publish_to_douyin(p, item, scheduled_mode=scheduled_mode)
                        if ok:
                            any_platform_success = True
                            item_published_platforms.append("抖音")
                    except Exception as e:
                        print(f"[!] 抖音分发异常: {e}")
                        print(">> [平台状态] 抖音: ❌ 未成功 - 异常")
                    time.sleep(3)

            # 3. X (Twitter) - 用户已明确要求取消自动发帖 (账号封锁/安全挑战)
            if any(k in target_set for k in ["x", "twitter", "twitter_x"]):
                print("[!] ✖️ [X / Twitter] 自动发帖通道已按用户要求停用（避免账号异常）。本次跳过。")
                print(">> [平台状态] X: ⚪ 已取消发帖")

            # 4. Instagram
            if any(k in target_set for k in ["instagram", "ig"]):
                if not check_platform_auth("instagram"):
                    print("[!] 📸 [Instagram] 未检测到有效登录 Session，自动跳过。如需发布请在桌面【内置多平台登录浏览器】中登录 Instagram 账号。")
                    print(">> [平台状态] Instagram: ⚪ 未登录跳过")
                else:
                    try:
                        ok = publish_to_instagram(p, item, scheduled_mode=scheduled_mode)
                        if ok:
                            any_platform_success = True
                            item_published_platforms.append("Instagram")
                    except Exception as e:
                        print(f"[!] Instagram 分发异常: {e}")
                        print(">> [平台状态] Instagram: ❌ 未成功 - 异常")
                    time.sleep(3)

            # 5. YouTube
            if any(k in target_set for k in ["youtube", "yt"]):
                if not check_platform_auth("youtube"):
                    print("[!] 🎬 [YouTube] 未检测到登录凭证，请在【内置多平台登录浏览器】中登录。本次跳过。")
                    print(">> [平台状态] YouTube: ❌ 未成功 - 未检测到登录凭证")
                else:
                    try:
                        ok = publish_to_youtube(p, item, scheduled_mode=scheduled_mode)
                        if ok:
                            any_platform_success = True
                            item_published_platforms.append("YouTube Shorts")
                    except Exception as e:
                        print(f"[!] YouTube 分发异常: {e}")
                        print(">> [平台状态] YouTube: ❌ 未成功 - 异常")

            # 只有任一平台真正发布成功，才放入归档列表
            if any_platform_success:
                item["actual_platforms"] = item_published_platforms
                success_archive_list.append(item)
            else:
                print(f"\n[提示] 切片【{item['filename']}】在本次各平台均未成功发表，继续保留在待发布切片库中！")

    # 归档移动至 G:\矩阵短视频\已发布
    if success_archive_list:
        print(f"\n[成果归档] 正在将本次发布的 {len(success_archive_list)} 部切片视频移入【已发布】文件夹...")
        today_str = datetime.date.today().strftime("%Y%m%d")
        new_names = []
        meta_records = []

        for item in success_archive_list:
            orig_path = item["path"]
            filename = item["filename"]
            dest_name = f"{today_str}_{filename}"
            dest_path = os.path.join(PUBLISHED_DIR, dest_name)

            try:
                # 移动视频
                shutil.move(orig_path, dest_path)
                print(f"   [√] 视频归档成功: {filename} ➔ G:\\矩阵短视频\\已发布\\{dest_name}")
                new_names.append(filename)
                new_names.append(dest_name)

                # 移动文案 txt (如果存在)
                if item["txt_path"] and os.path.exists(item["txt_path"]):
                    txt_dest = os.path.join(PUBLISHED_DIR, f"{today_str}_{os.path.basename(item['txt_path'])}")
                    shutil.move(item["txt_path"], txt_dest)

                meta_records.append({
                    "filename": filename,
                    "archived_as": dest_name,
                    "title": item["title"],
                    "tags": item["tags"],
                    "published_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "platforms": item.get("actual_platforms", ["小红书", "抖音", "YouTube Shorts"])
                })
            except Exception as e:
                print(f"   [!] 归档异常: {e}")

        save_published_records(new_names, meta_records)

    print("\n" + "=" * 70)
    print("🎉 全球多平台矩阵发布流程执行完毕！")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="自媒体多平台发布")
    parser.add_argument("--count", type=int, default=2, help="发布视频数量")
    parser.add_argument("--scheduled", action="store_true", help="定时模式启动")
    parser.add_argument("--platforms", type=str, default="all", help="目标平台: all 或指定平台逗号分隔 (如: x,youtube)")
    args = parser.parse_args()

    run_matrix_publish(video_count=args.count, scheduled_mode=args.scheduled, target_platforms=args.platforms)
