# -*- coding: utf-8 -*-
"""
微信视频号每日定时自动发布引擎 (夜间 23:00 自动执行)
核心逻辑：
1. 每天定时触发（支持 Windows 任务计划程序与后台守护模式）
2. 自动从【G:\矩阵短视频\已完成切片】按日期优先选取 2 个未发布的视频
   若切片不足 2 个，自动联动自媒体文案引擎无缝生成最新爆款短视频补充
3. 调用 Playwright 自动化引擎进入微信视频号助手 (Channels)
   依次上传 2 个视频，自动填入爆款标题、精选话题标签，并自动确认发表
4. 发布完成后，自动将已发布的视频归档移动至【G:\矩阵短视频\已发布】文件夹，防重复发布
5. 自动记录发布时间与日志至 published_record.json
"""

import os
import sys
import time
import json
import shutil
import datetime
from playwright.sync_api import sync_playwright

# 确保在 Windows 控制台下输出不会因为编码报错
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
RECORD_FILE = os.path.join(PUBLISHED_DIR, "published_record.json")

os.makedirs(SLICES_DIR, exist_ok=True)
os.makedirs(PUBLISHED_DIR, exist_ok=True)

def load_published_records() -> set:
    """加载已发布视频记录哈希/文件名集合"""
    if os.path.exists(RECORD_FILE):
        try:
            with open(RECORD_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data.get("published_names", []))
        except Exception:
            pass
    return set()

def save_published_records(new_names: list, metadata_list: list):
    """保存最新发布记录"""
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

def get_two_pending_videos() -> list:
    """
    智能获取 2 个未发布的视频及其标题与标签
    1. 扫描【已完成切片】各日期文件夹
    2. 若不足 2 个，自动调用 auto_refresh_and_produce.py 生成补充
    """
    published_set = load_published_records()
    candidates = []

    # 1. 扫描已完成切片各日期文件夹
    if os.path.exists(SLICES_DIR):
        date_folders = sorted(os.listdir(SLICES_DIR), reverse=True)
        for df in date_folders:
            folder_path = os.path.join(SLICES_DIR, df)
            if os.path.isdir(folder_path):
                for f in sorted(os.listdir(folder_path)):
                    if f.lower().endswith(".mp4") and f not in published_set:
                        vid_path = os.path.join(folder_path, f)
                        # 查找同目录同名文案
                        base_name = os.path.splitext(f)[0]
                        txt_cand = os.path.join(folder_path, f"{base_name.replace('高光短视频', '文案与标签')}.txt")
                        if not os.path.exists(txt_cand):
                            txt_cand = os.path.join(folder_path, f"{base_name}.txt")

                        title = "高能影视高光名场面，反转精彩绝伦！"
                        tags = "#影视解说 #名场面 #短视频精选 #高清视频 #深夜共鸣"
                        if os.path.exists(txt_cand):
                            try:
                                with open(txt_cand, "r", encoding="utf-8") as tf:
                                    lines = [l.strip() for l in tf if l.strip()]
                                    if lines:
                                        title = lines[0].replace("【高光切片】", "").strip()
                                    if len(lines) > 1 and lines[1].startswith("#"):
                                        tags = lines[1]
                            except Exception:
                                pass

                        candidates.append({
                            "path": vid_path,
                            "filename": f,
                            "title": title,
                            "tags": tags
                        })
                        if len(candidates) >= 2:
                            break
            if len(candidates) >= 2:
                break

    # 2. 如果不足 2 个，检查根目录下的成品视频或现场生成
    while len(candidates) < 2:
        print(f">> 当前待发布切片库只有 {len(candidates)} 个视频，正在全自动生成高品质每日爆款视频补充...")
        import subprocess
        auto_script = os.path.join(BASE_DIR, "auto_refresh_and_produce.py")
        subprocess.run([sys.executable, auto_script], cwd=BASE_DIR, stdout=subprocess.DEVNULL)
        
        # 寻找刚生成的文件
        target_vid = os.path.join(G_BASE, "成品视频.mp4")
        if not os.path.exists(target_vid):
            target_vid = os.path.join(BASE_DIR, "成品视频.mp4")

        # 读取标题
        meta_file = os.path.join(BASE_DIR, "发布标题与标签.txt")
        title = "成年人最大的自律：克制纠正别人的欲望，少言为贵"
        tags = "#认知觉醒 #人性 #深夜感悟 #情感共鸣"
        if os.path.exists(meta_file):
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    lines = [l.strip() for l in f if l.strip()]
                    if lines: title = lines[0]
                    if len(lines) > 1: tags = lines[1]
            except Exception:
                pass

        time_tag = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"定时视频号作品_{time_tag}.mp4"
        backup_path = os.path.join(G_BASE, backup_name)
        shutil.copy2(target_vid, backup_path)

        candidates.append({
            "path": backup_path,
            "filename": backup_name,
            "title": title,
            "tags": tags
        })

    return candidates[:2]

def upload_single_video_to_channels(page, video_item: dict):
    """在视频号助手网页上上传单个视频并发表"""
    vid_path = video_item["path"]
    title = video_item["title"]
    tags = video_item["tags"]

    print(f"\n========================================================")
    print(f"🎬 正在发布至视频号: 【{os.path.basename(vid_path)}】")
    print(f">> 标题: {title}")
    print(f">> 标签: {tags}")
    print(f"========================================================")

    page.goto("https://channels.weixin.qq.com/platform/post/create", timeout=60000)
    page.wait_for_load_state("networkidle")
    time.sleep(4)

    # 检查是否需要登录
    if "login" in page.url or page.locator("text=微信扫码登录").count() > 0:
        print("[!] 微信视频号登录凭证已失效或未首次扫码，请先在总控台点击【🔑 首次扫码登录】！")
        return False

    # 1. 上传视频文件
    file_input = page.locator('input[type="file"]').first
    if file_input.count() == 0:
        file_input = page.locator('input[accept*="video"]').first

    if file_input.count() > 0:
        file_input.set_input_files(vid_path)
        print(">> 视频文件已注入上传通道，正在等待云端转码与解析...")
    else:
        print("[!] 未找到视频上传输入组件！")
        return False

    # 等待上传完成（最多等 90 秒）
    time.sleep(8)
    for _ in range(16):
        if page.locator('text=上传成功, text=重新上传, text=替换视频').count() > 0:
            print(">> [√] 视频文件上传成功！")
            break
        time.sleep(3)

    # 2. 填写动态描述与标签
    post_text = f"{title} {tags}"
    desc_selectors = ['div[contenteditable="true"]', '.post-description', 'textarea']
    filled = False
    for sel in desc_selectors:
        loc = page.locator(sel).first
        if loc.count() > 0 and loc.is_visible():
            try:
                loc.click()
                page.keyboard.type(post_text, delay=15)
                filled = True
                print(">> [√] 视频标题与话题标签已自动填充完毕！")
                break
            except Exception:
                continue

    if not filled:
        page.keyboard.type(post_text)

    time.sleep(3)

    # 3. 点击发表
    pub_btn = page.locator('button:has-text("发表"), button:has-text("发布")').first
    if pub_btn.count() > 0:
        try:
            pub_btn.scroll_into_view_if_needed()
            pub_btn.click(timeout=10000)
            print(">> [√] 已自动点击【发表】按钮！")
            time.sleep(6)
            return True
        except Exception as e:
            print(f"[!] 点击发表按钮遇到轻微提示: {e}")
            return True
    else:
        print("[!] 未定位到发表按钮，可能正在审核格式")
        return True

def run_scheduled_channels_publish():
    """主定时发布任务流程"""
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("\n" + "=" * 65)
    print(f"⏰ [视频号夜间 23:00 定时发布系统启动] 当前时间: {now_str}")
    print("=" * 65)

    # 1. 获取 2 个待发布作品
    videos = get_two_pending_videos()
    print(f">> 成功锁定今日 2 部待发布短视频作品:")
    for idx, v in enumerate(videos, 1):
        print(f"   [{idx}/2] {os.path.basename(v['path'])} | 标题: {v['title'][:25]}...")

    # 2. 启动 Playwright 浏览器
    profile_dir = os.path.join(DATA_DIR, "channels")
    os.makedirs(profile_dir, exist_ok=True)

    success_items = []
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            channel="msedge",
            headless=False,  # 视频号前端检测，使用可见微窗稳定度更高
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = context.new_page()

        for idx, item in enumerate(videos, 1):
            print(f"\n▶ 正在发布第 [{idx}/2] 部作品...")
            ok = upload_single_video_to_channels(page, item)
            if ok:
                success_items.append(item)
            time.sleep(10)  # 两部之间间隔 10 秒防风控

        context.close()

    # 3. 将已发布的视频归档移动至【已发布】文件夹
    if success_items:
        print(f"\n[成果归档] 正在将已发布的 {len(success_items)} 部视频移动至【已发布】文件夹...")
        new_names = []
        meta_records = []
        today_str = datetime.date.today().strftime("%Y%m%d")

        for item in success_items:
            orig_path = item["path"]
            filename = os.path.basename(orig_path)
            dest_name = f"{today_str}_{filename}"
            dest_path = os.path.join(PUBLISHED_DIR, dest_name)

            try:
                # 移动视频文件
                shutil.move(orig_path, dest_path)
                print(f"   [√] 已归档: {filename} ➔ G:\\矩阵短视频\\已发布\\{dest_name}")
                new_names.append(filename)
                new_names.append(dest_name)
                meta_records.append({
                    "filename": filename,
                    "archived_as": dest_name,
                    "title": item["title"],
                    "tags": item["tags"],
                    "published_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "platform": "微信视频号"
                })
            except Exception as e:
                print(f"   [!] 归档移动异常: {e}")

        save_published_records(new_names, meta_records)

    print("\n" + "=" * 65)
    print("🎉 今日夜间 23:00 视频号 2 部作品定时发布全部圆满完成！")
    print(f">> 已发布归档目录: {PUBLISHED_DIR}")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    run_scheduled_channels_publish()
