# -*- coding: utf-8 -*-
"""
长视频资源全能下载与导入模块
功能：
1. 支持解析并高速下载全网主流平台长视频（B站、抖音、快手、YouTube、西瓜、微博等）
2. 支持直链（MP4/MKV/M3U8）防封高速直下
3. 支持一键下载官方精选高清电影示范片（带人声台词），方便用户立即体验切片流水线
4. 所有下载的长视频自动保存在【待切片长视频】素材目录中，供流水线直接切片
"""

import os
import sys
import re
import time
import urllib.request
import ssl
import subprocess
import argparse

# 确保在 Windows 控制台下输出不会因为编码报错
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_DIR = os.path.join(BASE_DIR, "待切片长视频")
os.makedirs(SOURCE_DIR, exist_ok=True)

# 精选高速影视示范片资源库（带对白台词、高画质）
DEMO_MOVIES = [
    {
        "name": "示范电影_辛特尔预告片(带台词高画质).mp4",
        "url": "https://media.w3.org/2010/05/sintel/trailer.mp4",
        "desc": "奇幻冒险电影预告片（含人声对白与激烈战斗场面）"
    },
    {
        "name": "示范纪录片_海洋自然奇观.mp4",
        "url": "https://vjs.zencdn.net/v/oceans.mp4",
        "desc": "BBC/迪士尼风格电影级海洋探索高清片"
    }
]

def download_file_with_progress(url: str, dest_path: str, desc: str = ""):
    """使用原生带防爬请求头的高速流式下载，带进度显示"""
    print(f">> 正在连接下载节点: {url}")
    if desc:
        print(f">> 素材说明: {desc}")
        
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    ssl_ctx = ssl._create_unverified_context()
    req = urllib.request.Request(url, headers=headers)
    
    with urllib.request.urlopen(req, timeout=30, context=ssl_ctx) as response:
        total_size = int(response.headers.get("Content-Length", 0))
        chunk_size = 1024 * 128
        downloaded = 0
        start_time = time.time()
        
        with open(dest_path, "wb") as f:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    percent = downloaded / total_size * 100
                    speed = downloaded / (time.time() - start_time + 0.001) / 1024
                    sys.stdout.write(f"\r   [下载进度] {downloaded/(1024*1024):.2f}MB / {total_size/(1024*1024):.2f}MB ({percent:.1f}%) | 速度: {speed:.1f} KB/s")
                    sys.stdout.flush()
        print("\n")
    print(f"[√] 下载完成！已存入: {dest_path}")
    return dest_path

def download_online_video(url: str) -> str:
    """自动判断类型并下载视频"""
    url = url.strip(' "\'')
    if not url:
        print("[!] 请提供有效的视频网址！")
        return ""

    # 1. 如果是直接的媒体文件直链 (.mp4, .mkv 等)
    lower_url = url.lower().split("?")[0]
    if any(lower_url.endswith(ext) for ext in [".mp4", ".mkv", ".webm", ".avi", ".mov"]):
        filename = os.path.basename(lower_url)
        if not filename or len(filename) < 4:
            filename = f"web_video_{int(time.time())}.mp4"
        dest_path = os.path.join(SOURCE_DIR, filename)
        return download_file_with_progress(url, dest_path, "直链媒体素材")

    # 2. 如果是 M3U8 流媒体链接 (如猫抓嗅探到的地址)
    if ".m3u8" in url.lower():
        print(f"\n>> 检测到 M3U8 流媒体链接 (猫抓嗅探源)，正在调用 FFmpeg 无损高速合并下载...")
        out_name = f"m3u8_stream_{int(time.time())}.mp4"
        dest_path = os.path.join(SOURCE_DIR, out_name)
        ffmpeg_exe = r"C:\Windows\System32\ffmpeg.exe"
        cmd = [
            ffmpeg_exe, "-y",
            "-headers", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\r\n",
            "-i", url,
            "-c", "copy",
            "-bsf:a", "aac_adtstoasc",
            dest_path
        ]
        res = subprocess.run(cmd)
        if res.returncode == 0 and os.path.exists(dest_path) and os.path.getsize(dest_path) > 10000:
            print(f"\n[√] M3U8 影视流已成功下载并合并为 MP4: {dest_path}")
            return dest_path

    # 3. 如果是主流自媒体/视频平台网页（调用 yt-dlp 深度解析）
    print(f"\n>> 正在调用 yt-dlp 解析平台网页视频: {url}")
    output_tpl = os.path.join(SOURCE_DIR, "%(title).50s [%(id)s].%(ext)s")
    
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--no-playlist",
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "-o", output_tpl,
        "--extractor-args", "generic:impersonate",
        url
    ]
    
    try:
        proc = subprocess.run(cmd, text=True)
        if proc.returncode == 0:
            print("\n[√] 平台视频已全自动解析并下载完成！")
            # 找到最新的文件
            files = [os.path.join(SOURCE_DIR, f) for f in os.listdir(SOURCE_DIR) if not f.endswith(".tmp")]
            if files:
                latest_file = max(files, key=os.path.getmtime)
                print(f">> 视频文件: {os.path.basename(latest_file)}")
                return latest_file
        else:
            print(f"\n[!] yt-dlp 下载遇到问题，返回值: {proc.returncode}")
    except Exception as e:
        print(f"\n[!] 下载异常: {e}")
    return ""

def download_demo_movie(index: int = 0) -> str:
    """一键下载官方影视示范长视频素材"""
    if index >= len(DEMO_MOVIES):
        index = 0
    movie = DEMO_MOVIES[index]
    dest_path = os.path.join(SOURCE_DIR, movie["name"])
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 100000:
        print(f">> 影视示范素材已存在: {movie['name']} ({os.path.getsize(dest_path)/(1024*1024):.2f} MB)")
        return dest_path
    
    print(f"\n[一键获取示范片] 正在下载电影示范长视频: 《{movie['name']}》...")
    return download_file_with_progress(movie["url"], dest_path, movie["desc"])

def main():
    parser = argparse.ArgumentParser(description="长视频资源全能下载与导入")
    parser.add_argument("--url", type=str, default="", help="视频网页链接或直链")
    parser.add_argument("--demo", action="store_true", help="一键下载官方影视示范片")
    args = parser.parse_args()

    print("========================================================")
    print("   📥 长视频素材资源下载与导入中心")
    print("========================================================")
    print(f"素材存放目录: {SOURCE_DIR}\n")

    if args.demo:
        path = download_demo_movie(0)
        print(f"示范片准备就绪: {path}")
        return

    url = args.url
    if not url:
        print("💡 请输入视频链接（支持 B站、YouTube、抖音、快手、直链等）：")
        print("（输入 demo 可以直接下载高画质电影示范片）")
        try:
            url = input("👉 请输入视频链接: ").strip()
        except Exception:
            url = ""

    if url.lower() == "demo":
        download_demo_movie(0)
    elif url:
        download_online_video(url)
    else:
        print("未输入链接，正在下载示范电影片供体验...")
        download_demo_movie(0)

if __name__ == "__main__":
    main()
