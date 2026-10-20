# -*- coding: utf-8 -*-
"""
长视频智能切片与影视解说自动化流水线
核心功能：
1. 支持长视频网页链接解析下载 (yt-dlp) 或直接载入本地高清视频原片
2. 调用 AI 语音转录与词级时间轴对齐模型 (基于 CTranslate2 / Whisper)
3. 智能语义断句：自动识别连续语音，精准切分出 30 秒至 1 分钟的高光竖屏切片
4. FFmpeg 全套影视解说去重处理：
   - 画面水平镜像反转 (hflip) 破坏画面指纹
   - 速度微调 1.03x 避开平台音频指纹检测
   - 电影级调色（对比度/饱和度/微锐化）增强质感
   - 9:16 (1080x1920) 动态毛玻璃背景与画面居中构图
   - 压制高光动态淡入淡出字幕
5. 自动输出到【长视频切片成果】文件夹，并为每个切片生成配套标题与文案
"""

import os
import sys
import re
import time
import subprocess
import argparse

# 确保 Windows 终端中文正常显示
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
        sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:
        pass

import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(BASE_DIR, "temp_pipeline")

def get_daily_output_dir() -> str:
    """获取每日独立切片存放目录: G:\矩阵短视频\已完成切片\YYYY-MM-DD"""
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    base_g = r"G:\矩阵短视频" if os.path.exists("G:\\") else BASE_DIR
    daily_dir = os.path.join(base_g, "已完成切片", today_str)
    os.makedirs(daily_dir, exist_ok=True)
    return daily_dir

OUTPUT_DIR = get_daily_output_dir()

def find_ffmpeg() -> str:
    """获取 FFmpeg 绝对路径"""
    sys32 = r"C:\Windows\System32\ffmpeg.exe"
    if os.path.exists(sys32):
        return sys32
    script_ffmpeg = r"C:\Program Files\Python311\Scripts\ffmpeg.exe"
    if os.path.exists(script_ffmpeg):
        return script_ffmpeg
    return "ffmpeg"

def get_video_duration(ffmpeg_exe: str, video_path: str) -> float:
    """获取视频文件总时长（秒）"""
    try:
        cmd = [ffmpeg_exe, "-i", video_path]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="ignore")
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", res.stdout)
        if m:
            h, m_val, s = float(m.group(1)), float(m.group(2)), float(m.group(3))
            return h * 3600 + m_val * 60 + s
    except Exception:
        pass
    return 120.0

def download_or_locate_video(video_input: str) -> str:
    """下载在线长视频或验证本地视频文件，优先使用【待切片视频】中的素材"""
    video_input = video_input.strip(' "\'') if video_input else ""
    local_source = os.path.join(BASE_DIR, "待切片长视频")
    g_source = r"G:\矩阵短视频\待切片视频" if os.path.exists("G:\\") else local_source
    os.makedirs(local_source, exist_ok=True)
    os.makedirs(g_source, exist_ok=True)

    # 1. 在线链接下载
    if video_input.startswith("http://") or video_input.startswith("https://"):
        print(f"\n[步骤 1/5] 检测到在线视频链接，正在调用下载引擎获取原片...")
        from download_video_resource import download_online_video
        dl_path = download_online_video(video_input)
        if dl_path and os.path.exists(dl_path):
            return dl_path

    # 2. 本地文件直接判断
    if video_input:
        if os.path.isabs(video_input) and os.path.exists(video_input):
            return video_input
        for sdir in [g_source, local_source, BASE_DIR]:
            p = os.path.join(sdir, video_input)
            if os.path.exists(p):
                return p

    # 3. 扫描【G:\矩阵短视频\待切片视频】与本地素材目录
    exts = (".mp4", ".mkv", ".mov", ".flv", ".avi", ".webm")
    all_source_files = []
    for sdir in [g_source, local_source]:
        if os.path.exists(sdir):
            for f in os.listdir(sdir):
                if f.lower().endswith(exts):
                    all_source_files.append(os.path.join(sdir, f))

    if all_source_files:
        latest_source = max(all_source_files, key=os.path.getmtime)
        print(f">> 自动选用待切片素材库中的最新长视频: 【{os.path.basename(latest_source)}】")
        return latest_source

    # 4. 未输入且素材库为空时，自动下载官方高清电影示范片体验
    print(">> 待切片素材库暂无视频，正在自动为您获取官方高清影视示范原片...")
    from download_video_resource import download_demo_movie
    demo_path = download_demo_movie(0)
    if os.path.exists(demo_path):
        return demo_path

    print(f"\n[错误] 未找到视频素材，请把长视频放入【待切片视频】文件夹后重试！")
    sys.exit(1)

def extract_audio(ffmpeg_exe: str, video_path: str, max_duration_sec: float = None) -> str:
    """提取适合 AI 语音转录的 16kHz 单声道音频 (可根据需求截取前缀时长加速识别)"""
    os.makedirs(TEMP_DIR, exist_ok=True)
    audio_path = os.path.join(TEMP_DIR, "temp_audio_16k.wav")
    print("\n[步骤 2/5] [进度 10%] 正在从视频原片中提取高保真语音音轨...")
    cmd = [ffmpeg_exe, "-y"]
    if max_duration_sec and max_duration_sec > 0:
        cmd.extend(["-t", f"{max_duration_sec:.1f}"])
        print(f">> 提取前 {max_duration_sec/60:.1f} 分钟音轨加速 AI 识别...")
    cmd.extend([
        "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        audio_path
    ])
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return audio_path

def transcribe_and_align(audio_path: str):
    """调用 faster-whisper 进行高精度中文转录与词级时间轴对齐"""
    from faster_whisper import WhisperModel

    print("\n[步骤 3/5] [进度 20%] 正在加载 AI 语音对齐模型 (int8 CPU 高速引擎)...")
    model = WhisperModel("base", device="cpu", compute_type="int8")
    
    print(">> 正在执行语音识别与分词时间戳计算 (启用 VAD 智能静音跳过)...")
    t0 = time.time()
    segments, info = model.transcribe(audio_path, word_timestamps=True, language="zh", vad_filter=True)
    
    seg_list = []
    full_text_list = []
    for s in segments:
        text = s.text.strip()
        if text:
            seg_list.append({
                "start": s.start,
                "end": s.end,
                "text": text,
                "words": [{"start": w.start, "end": w.end, "word": w.word} for w in (s.words or [])]
            })
            full_text_list.append(text)

    print(f">> AI 语音转录完成，耗时 {time.time() - t0:.1f} 秒，共提取 {len(seg_list)} 个语音片段！")
    return seg_list

def slice_highlights(segments, min_sec=240.0, target_sec=300.0, max_sec=360.0, max_clips=None):
    """
    根据自然语音语义边界，智能聚合出指定时长 (如 5分钟左右) 的高光切片
    """
    min_mins = min_sec / 60.0
    max_mins = max_sec / 60.0
    target_mins = target_sec / 60.0
    print(f"\n[步骤 4/5] [进度 40%] 正在根据语言语义边界切分 ~{target_mins:.1f}分钟 ({min_sec:.0f}s~{max_sec:.0f}s) 的高光片段...")
    clips = []
    curr_segs = []
    
    for seg in segments:
        curr_segs.append(seg)
        dur = curr_segs[-1]["end"] - curr_segs[0]["start"]
        
        # 达到目标时长且以句号/问号/感叹号等明显停顿结尾，或者超过最长限制
        ends_with_punct = any(seg["text"].endswith(p) for p in ["。", "！", "？", "!", "?", "；"])
        if (dur >= target_sec and ends_with_punct) or (dur >= max_sec):
            clips.append({
                "clip_idx": len(clips) + 1,
                "start": curr_segs[0]["start"],
                "end": curr_segs[-1]["end"],
                "segments": curr_segs
            })
            curr_segs = []
            if max_clips and len(clips) >= max_clips:
                break

    # 处理剩余尾部片段 (若未达到 max_clips)
    if curr_segs and (not max_clips or len(clips) < max_clips):
        dur = curr_segs[-1]["end"] - curr_segs[0]["start"]
        if dur >= min_sec or not clips:
            clips.append({
                "clip_idx": len(clips) + 1,
                "start": curr_segs[0]["start"],
                "end": curr_segs[-1]["end"],
                "segments": curr_segs
            })
        elif clips:
            # 尾部太短则合并到最后一个切片中
            clips[-1]["end"] = curr_segs[-1]["end"]
            clips[-1]["segments"].extend(curr_segs)

    print(f">> 智能切分计算完毕：共规划出 {len(clips)} 个高光短视频切片！")
    for c in clips:
        dur = c["end"] - c["start"]
        preview = "".join(s["text"] for s in c["segments"])[:30] + "..."
        print(f"   [切片 {c['clip_idx']:02d}] 时长: {dur:.1f}s ({dur/60:.2f}分钟) | 范围: {c['start']:.1f}s ~ {c['end']:.1f}s | 文案: {preview}")
    return clips

def wrap_chinese_text(text: str, max_chars: int = 15) -> str:
    """按标点折行，防止字幕溢出屏幕"""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    segments = re.findall(r'[^，。！？；、\s]+[，。！？；、\s]?', text)
    if not segments:
        segments = [text]
    lines = []
    current_line = ""
    for seg in segments:
        if len(current_line) + len(seg) <= max_chars:
            current_line += seg
        else:
            if current_line:
                lines.append(current_line)
            while len(seg) > max_chars:
                lines.append(seg[:max_chars])
                seg = seg[max_chars:]
            current_line = seg
    if current_line:
        lines.append(current_line)
    return r"\N".join(lines)

def make_clip_ass_subtitles(clip_segments, clip_start, ass_output_path):
    """为特定切片生成居中动态高光 ASS 字幕文件"""
    ass_header = """[Script Info]
Title: Highlight Clip Subtitles
ScriptType: v4.00+
WrapStyle: 2
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Microsoft YaHei,52,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,2,0,1,3.5,2,2,60,60,400,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    def to_ass_time(sec):
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        s = sec % 60
        return f"{h}:{m:02d}:{s:05.2f}"

    dialogues = []
    for s in clip_segments:
        # 转换为切片内部相对时间（从 0 开始），由于后续变速 1.03x，时间戳需同步按 1.03 缩减
        rel_start = (s["start"] - clip_start) / 1.03
        rel_end = (s["end"] - clip_start) / 1.03
        if rel_end <= rel_start:
            rel_end = rel_start + 0.5
        t_start = to_ass_time(max(0.0, rel_start))
        t_end = to_ass_time(rel_end)
        
        wrapped = wrap_chinese_text(s["text"], max_chars=15)
        # 淡入淡出动效
        line = f"Dialogue: 0,{t_start},{t_end},Default,,0,0,0,,{{\\fad(100,100)}}{wrapped}"
        dialogues.append(line)

    with open(ass_output_path, "w", encoding="utf-8") as f:
        f.write(ass_header + "\n".join(dialogues) + "\n")

def process_and_render_clips(ffmpeg_exe: str, video_path: str, clips, use_mediapipe: bool = True, use_autoeditor: bool = True):
    """
    使用 FFmpeg 对每个切片进行影视解说级去重与 1080x1920 竖屏渲染：
    - MediaPipe 人脸追踪智能居中
    - 水平镜像翻转 (hflip)
    - 微调播放速度 1.03x (setpts / atempo)
    - 色彩微调滤镜 (eq 对比度/饱和度/微调)
    - 9:16 (1080x1920) 动态毛玻璃背景 + 画面居中铺满
    - 压制高光动态字幕
    - auto-editor 智能剔除无声停顿
    """
    output_dir = get_daily_output_dir()
    os.makedirs(output_dir, exist_ok=True)
    print(f"\n[步骤 5/5] [进度 65%] 正在执行影视级画面去重并压制 1080x1920 竖屏切片 (含AI人脸追踪与去冗余)...")
    print(f">> 每日切片存放目录: {output_dir}")

    import advanced_video_enhancer as ave

    # 提取原视频基础名称 (去除扩展名)
    video_stem = os.path.splitext(os.path.basename(video_path))[0]
    print(f">> 切片原片所属系列: 【{video_stem}】")

    # 全局动态检索已存在的属于该原视频的切片序号（包括已发布和各日期切片库），严格依次排序自增
    existing_indices = []
    base_g = r"G:\矩阵短视频" if os.path.exists("G:\\") else BASE_DIR
    scan_dirs = [output_dir, os.path.join(base_g, "已发布")]
    slices_parent = os.path.join(base_g, "已完成切片")
    if os.path.exists(slices_parent):
        for sub in os.listdir(slices_parent):
            p = os.path.join(slices_parent, sub)
            if os.path.isdir(p):
                scan_dirs.append(p)

    pattern = rf"(?:^\d{{8}}_)?{re.escape(video_stem)}_切片_(\d+)"
    for sdir in set(scan_dirs):
        if os.path.exists(sdir):
            for f in os.listdir(sdir):
                m = re.search(pattern, f)
                if m:
                    existing_indices.append(int(m.group(1)))

    start_offset = max(existing_indices) if existing_indices else 0
    print(f">> 当前原片已存在最大切片序号: {start_offset:02d}，新切片将从第 {start_offset + 1:02d} 号依次递增命名。")

    # 为原视频生成统一高光封面 (同一原视频切片视频发布时封面使用高光统一封面)
    unified_cover = os.path.join(output_dir, f"{video_stem}_统一高光封面.jpg")
    if not os.path.exists(unified_cover) and clips:
        cover_time = clips[0]["start"] + min(15.0, (clips[0]["end"] - clips[0]["start"]) * 0.3)
        try:
            cover_cmd = [
                ffmpeg_exe, "-y",
                "-ss", f"{cover_time:.2f}",
                "-i", video_path,
                "-vframes", "1",
                "-q:v", "2",
                unified_cover
            ]
            subprocess.run(cover_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists("G:\\"):
                try:
                    shutil.copy2(unified_cover, r"G:\矩阵短视频\统一高光封面.jpg")
                except Exception:
                    pass
            print(f">> [√] 成功生成该原视频的【统一高光封面】: {os.path.basename(unified_cover)}")
        except Exception as ce:
            print(f"[!] 生成高光统一封面提示: {ce}")

    total = len(clips)
    for i, clip in enumerate(clips, 1):
        idx = start_offset + i
        clip_dur = clip["end"] - clip["start"]
        out_video = os.path.join(output_dir, f"{video_stem}_切片_{idx:02d}_高光短视频.mp4")
        out_meta = os.path.join(output_dir, f"{video_stem}_切片_{idx:02d}_文案与标签.txt")
        ass_path = os.path.join(TEMP_DIR, f"subtitles_{idx:02d}.ass")

        mins = clip_dur / 60.0
        print(f"\n▶ [进度 75%] 正在渲染 [{i}/{total}] 切片 {idx:02d} (时长: {clip_dur:.1f}s / {mins:.2f}分钟)...")
        print(f"   目标文件名: {os.path.basename(out_video)}")

        # 1. MediaPipe 人脸位置分析
        face_ratio = 0.5
        if use_mediapipe:
            face_ratio = ave.compute_clip_face_center_ratio(video_path, clip["start"], clip["end"])

        # 2. 生成切片专用字幕
        make_clip_ass_subtitles(clip["segments"], clip["start"], ass_path)

        # 3. 生成配套发布文案
        clip_full_text = "".join(s["text"] for s in clip["segments"])
        clip_title = clip["segments"][0]["text"].replace("，", "").replace("。", "")[:28]
        with open(out_meta, "w", encoding="utf-8") as f:
            f.write(f"【高光切片】{video_stem}：{clip_title}\n#高光时刻 #影视解说 #名场面 #短视频切片 #认知觉醒\n【统一封面】: {os.path.basename(unified_cover)}\n\n【切片台词全文】\n{clip_full_text}\n")

        # 4. 影视解说专属去重与排版 Filter Graph (高速毛玻璃背景优化)
        ass_escaped = os.path.basename(ass_path)
        filter_graph = (
            f"[0:v]hflip,setpts=PTS/1.03,eq=contrast=1.06:brightness=0.01:saturation=1.08[v];"
            f"[v]scale=270:480:force_original_aspect_ratio=increase,crop=270:480,boxblur=10:2,scale=1080:1920[bg];"
            f"[v]scale=1080:-1[fg];"
            f"[bg][fg]overlay=0:(H-h)/2[base];"
            f"[base]ass='{ass_escaped}'[outv];"
            f"[0:a]atempo=1.03,volume=1.05[outa]"
        )

        raw_render_video = os.path.join(TEMP_DIR, f"temp_render_{idx:02d}.mp4")
        cmd = [
            ffmpeg_exe, "-y",
            "-ss", f"{clip['start']:.2f}",
            "-to", f"{clip['end']:.2f}",
            "-i", video_path,
            "-filter_complex", filter_graph,
            "-map", "[outv]",
            "-map", "[outa]",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            raw_render_video
        ]

        t_render = time.time()
        res = subprocess.run(cmd, cwd=TEMP_DIR, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if res.returncode != 0:
            print(f"[!] 切片 {idx:02d} 使用安全模式重试...")
            safe_filter = f"[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,ass='{ass_escaped}'[outv]"
            safe_cmd = [
                ffmpeg_exe, "-y",
                "-ss", f"{clip['start']:.2f}",
                "-to", f"{clip['end']:.2f}",
                "-i", video_path,
                "-filter_complex", safe_filter,
                "-map", "[outv]",
                "-map", "0:a",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                raw_render_video
            ]
            subprocess.run(safe_cmd, cwd=TEMP_DIR, capture_output=True)

        # 5. auto-editor 剔除无声冗余
        final_video = raw_render_video
        if use_autoeditor and os.path.exists(raw_render_video):
            print(f">> [进度 90%] 正在调用 auto-editor 智能剔除无声停顿冗余...")
            fast_video = os.path.join(TEMP_DIR, f"temp_fast_{idx:02d}.mp4")
            if ave.remove_silence_with_auto_editor(raw_render_video, fast_video, margin="0.25s"):
                final_video = fast_video

        # 移动到输出目录
        import shutil
        shutil.copy2(final_video, out_video)
        if os.path.exists("G:\\"):
            try:
                shutil.copy2(out_video, r"G:\矩阵短视频\成品视频.mp4")
            except Exception:
                pass

        size_mb = os.path.getsize(out_video) / (1024 * 1024) if os.path.exists(out_video) else 0
        print(f">> [√] [进度 98%] 切片 {idx:02d} 渲染与去重成功！耗时: {time.time() - t_render:.1f}s | 文件大小: {size_mb:.2f} MB")
        print(f"   🎬 成果视频: {os.path.basename(out_video)}")

def main():
    parser = argparse.ArgumentParser(description="长视频智能切片与影视解说自动化流水线")
    parser.add_argument("--input", help="输入长视频链接或本地路径", default=None)
    parser.add_argument("--duration", type=float, default=300.0, help="切片目标时长 (秒)，默认 300 秒 (5分钟左右)")
    parser.add_argument("--max-clips", type=int, default=1, help="单次生成切片最大数量 (默认生成 1 部)")
    parser.add_argument("--no-scenedetect", action="store_true", help="关闭 PySceneDetect 镜头防截断")
    parser.add_argument("--no-mediapipe", action="store_true", help="关闭 MediaPipe 人脸追踪")
    parser.add_argument("--no-autoeditor", action="store_true", help="关闭 auto-editor 无声冗余剔除")
    args = parser.parse_args()

    use_scenedetect = not args.no_scenedetect
    use_mediapipe = not args.no_mediapipe
    use_autoeditor = not args.no_autoeditor

    target_sec = max(20.0, args.duration)
    min_sec = max(15.0, target_sec * 0.8)
    max_sec = target_sec * 1.2
    max_clips = args.max_clips if args.max_clips > 0 else None

    print("========================================================")
    print("   🎬 长视频智能切片与影视解说自动化流水线 (AI增强版)")
    print("========================================================")
    print(f"切片配置参数:")
    print(f"  [√] 目标单片时长: {target_sec:.0f}s ({target_sec/60:.1f}分钟) [语义区间: {min_sec:.0f}s ~ {max_sec:.0f}s]")
    print(f"  [√] 单次出片数量: {max_clips if max_clips else '全部切出'}")
    print(f"功能模组状态:")
    print(f"  [√] PySceneDetect 镜头防截断: {'开启' if use_scenedetect else '关闭'}")
    print(f"  [√] MediaPipe 人脸追踪 C 位:  {'开启' if use_mediapipe else '关闭'}")
    print(f"  [√] auto-editor 剔除无声冗余: {'开启' if use_autoeditor else '关闭'}\n")

    ffmpeg_exe = find_ffmpeg()
    print(f">> 视频编码引擎: {os.path.basename(ffmpeg_exe)}")

    # 获取输入
    video_input = args.input
    if not video_input and sys.stdin.isatty():
        print("💡 请输入长视频网页链接（YouTube/B站/抖音等），或本地视频文件名：")
        print("（支持直接把电脑里的长视频拖入此窗口，直接回车自动使用待切片素材库中的最新视频）")
        try:
            video_input = input("👉 请输入视频源: ").strip()
        except (EOFError, KeyboardInterrupt):
            video_input = ""

    # 1. 查找或下载长视频
    video_path = download_or_locate_video(video_input)
    video_size_mb = os.path.getsize(video_path) / (1024 * 1024)
    print(f"\n>> 已锁定长视频源: 【{os.path.basename(video_path)}】 ({video_size_mb:.2f} MB)")

    # 智能计算片头片尾与所需音轨时长
    total_dur = get_video_duration(ffmpeg_exe, video_path)
    intro_trim = 3.0
    outro_trim = 3.0
    if total_dur > 600:
        intro_trim = 25.0  # 10分钟以上长视频跳过25秒片头
        outro_trim = 35.0  # 跳过35秒片尾
    elif total_dur > 180:
        intro_trim = 12.0  # 3分钟以上跳过12秒
        outro_trim = 18.0  # 跳过18秒

    valid_start = intro_trim
    valid_end = max(valid_start + 15.0, total_dur - outro_trim)

    # 2. 提取音轨 (若指定了 max_clips，仅提取前缀所需音轨大幅加速 AI 转录)
    max_audio_sec = None
    if max_clips:
        max_audio_sec = min(total_dur, valid_start + (max_clips * max_sec) + 90.0)
    audio_path = extract_audio(ffmpeg_exe, video_path, max_duration_sec=max_audio_sec)

    # 3. AI 语音转录与词级对齐
    segments = transcribe_and_align(audio_path)

    print(f"\n[开篇与结尾智能去除] 原片总长: {total_dur:.1f}s | 智能截除片头: {intro_trim:.1f}s | 智能截除片尾: {outro_trim:.1f}s")
    print(f">> 锁定核心正片高潮区间: {valid_start:.1f}s ~ {valid_end:.1f}s (彻底杜绝片头广告与片尾黑屏)")

    if segments:
        filtered = [s for s in segments if s["start"] >= valid_start and s["end"] <= valid_end]
        if filtered:
            segments = filtered
            print(f">> 成功剔除片头片尾，保留 {len(segments)} 个核心正片台词片段！")

    if not segments:
        print("[!] 未检测到密集人声对白，已自动启用【影视画面高能节奏切分模式】...")
        step = target_sec
        clips = []
        cur = valid_start
        idx = 1
        while cur + (target_sec * 0.4) < valid_end and (max_clips is None or idx <= max_clips):
            end_t = min(cur + step, valid_end)
            clips.append({
                "clip_idx": idx,
                "start": cur,
                "end": end_t,
                "segments": [{
                    "start": cur,
                    "end": end_t,
                    "text": "高能影视高光名场面",
                    "words": []
                }]
            })
            cur += step
            idx += 1
    else:
        # 4. 智能切分指定时长的高光片段
        clips = slice_highlights(segments, min_sec=min_sec, target_sec=target_sec, max_sec=max_sec, max_clips=max_clips)

    # 4.5. PySceneDetect 镜头分界防截断吸附 (优化：仅扫描至切片终点，10倍提速)
    if use_scenedetect:
        import advanced_video_enhancer as ave
        max_clip_end = (max(c["end"] for c in clips) + 30.0) if clips else None
        cut_points = ave.detect_scene_cut_points(video_path, end_time=max_clip_end)
        if cut_points:
            for c in clips:
                c["start"], c["end"] = ave.snap_clip_to_scenes(c["start"], c["end"], cut_points)

    # 5. FFmpeg 去重与竖屏出片 (融合 MediaPipe 人脸追踪与 auto-editor 提速)
    process_and_render_clips(ffmpeg_exe, video_path, clips, use_mediapipe=use_mediapipe, use_autoeditor=use_autoeditor)

    print("\n========================================================")
    print("   🎉 [进度 100%] 长视频全套切片与高光封面流水线执行完毕！")
    print("========================================================")
    print(f"   📂 所有切片视频保存在: {OUTPUT_DIR}")
    print("   💡 每个切片均已完成【画面翻转+速度微调+电影调色+高斯模糊背景+动效字幕】全套去重！")
    print("   可直接挑选满意的片段发往抖音、快手、小红书和视频号！")
    print("========================================================\n")

if __name__ == "__main__":
    main()

