# -*- coding: utf-8 -*-
"""
自媒体全自动短视频工厂
全流程自动化：
1. 读取【今日文案.txt】
2. 调用微软云端 edge-tts 真人语音合成【配音.mp3】与高精度时间轴【字幕.srt】
3. 智能排版将字幕转换为 1080x1920 居中动态美化字幕【字幕.ass】（自带优雅淡入淡出动效、智能断句折行、防出界溢出保护）
4. 调用 FFmpeg 一键渲染压制为高规格竖屏【成品视频.mp4】（黑底白字居中、H.264高画质、全平台兼容）
"""

import os
import sys
import re
import asyncio
import subprocess
import argparse

# 确保在 Windows 控制台下输出不会因为编码报错
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

VOICES = {
    "1": ("zh-CN-YunxiNeural", "云希 (男声 | 深沉质感、深夜情感、认知觉醒爆款专用)"),
    "2": ("zh-CN-XiaoxiaoNeural", "晓晓 (女声 | 温柔知性、情感叙事、治愈共鸣专用)"),
}

def find_ffmpeg() -> str:
    """查找可用的 ffmpeg 可执行文件路径"""
    # 1. 检查 System32
    sys32_ffmpeg = r"C:\Windows\System32\ffmpeg.exe"
    if os.path.exists(sys32_ffmpeg):
        return sys32_ffmpeg

    # 2. 检查 Python Scripts 目录
    script_ffmpeg = r"C:\Program Files\Python311\Scripts\ffmpeg.exe"
    if os.path.exists(script_ffmpeg):
        return script_ffmpeg

    # 3. 检查 imageio_ffmpeg
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if os.path.exists(exe):
            return exe
    except Exception:
        pass

    return "ffmpeg"

def load_text(file_path: str) -> str:
    """读取文案文件，兼容多种编码格式"""
    if not os.path.exists(file_path):
        print(f"\n[错误] 未找到文案文件: {file_path}")
        print("正在为您创建默认的【今日文案.txt】...")
        default_content = (
            "成年人的世界，很多时候不是你不优秀，而是你太懂事了。\n"
            "你习惯了替所有人着想，却唯独忘了心疼自己；你总以为掏心掏肺就能换来珍惜，最后却发现，廉价的付出换来的只有理所当然。\n"
            "人性最大的弱点，就是永远记不住轻易得到的好。\n"
            "从今天起，收起你泛滥的善良。不是每个人都配得上你的真诚，当你开始学会拒绝、学会把精力留给自己，你才会发现，真正的高贵，是从不在烂人烂事上消耗自己。"
        )
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(default_content)
        return default_content

    for encoding in ["utf-8-sig", "utf-8", "gbk", "gb18030"]:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                content = f.read().strip()
                if content:
                    return content
        except (UnicodeDecodeError, LookupError):
            continue

    print(f"\n[错误] 文件 {file_path} 内容为空或编码无法解析！")
    sys.exit(1)

def choose_voice(voice_arg: str = None) -> tuple:
    """选择配音音色"""
    if voice_arg:
        voice_lower = voice_arg.lower()
        if "yunxi" in voice_lower or voice_lower == "1" or "云希" in voice_lower:
            return VOICES["1"]
        elif "xiaoxiao" in voice_lower or voice_lower == "2" or "晓晓" in voice_lower:
            return VOICES["2"]
        else:
            return (voice_arg, f"自定义语音: {voice_arg}")

    print("\n========================================================")
    print("   [配音音色选择]")
    print("========================================================")
    for key, (voice_id, desc) in VOICES.items():
        print(f"  [{key}] {desc}")
    print("--------------------------------------------------------")
    
    try:
        choice = input(">> 请输入数字选择 (直接按回车默认选 1 云希): ").strip()
    except (EOFError, KeyboardInterrupt):
        choice = "1"
    
    if not choice or choice not in VOICES:
        choice = "1"
    
    return VOICES[choice]

async def generate_voice_and_subtitles(text: str, voice: str, output_audio: str, output_srt: str, max_retries: int = 3):
    """调用 edge-tts 生成音频与字幕，内置网络超时重试保护"""
    import edge_tts

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            retry_tag = f" (第 {attempt} 次尝试)" if attempt > 1 else ""
            print(f"\n[步骤 1/4] 正在连接微软云端语音引擎{retry_tag}...")
            communicate = edge_tts.Communicate(text, voice)
            submaker = edge_tts.SubMaker()
            
            print("[步骤 2/4] 正在合成高清配音并同步计算字幕时间轴...")
            audio_data = bytearray()

            async def _stream():
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_data.extend(chunk["data"])
                    elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                        submaker.feed(chunk)

            await asyncio.wait_for(_stream(), timeout=35.0)

            with open(output_audio, "wb") as f:
                f.write(audio_data)

            srt_content = submaker.get_srt()
            with open(output_srt, "w", encoding="utf-8") as f:
                f.write(srt_content)

            return
        except (asyncio.TimeoutError, Exception) as e:
            last_error = e
            if attempt < max_retries:
                print(f"[!] 网络微弱波动 ({e})，2 秒后自动重新尝试...")
                await asyncio.sleep(2)
            else:
                raise last_error

def wrap_chinese_text(text: str, max_chars: int = 15) -> str:
    """按标点符号与自然断句优雅折行，确保每行不超过 max_chars，避免字幕溢出屏幕"""
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

def convert_srt_to_ass(srt_file: str, ass_file: str):
    """将 SRT 转换为 1080x1920 居中高清动态美化 ASS 字幕"""
    with open(srt_file, "r", encoding="utf-8") as f:
        srt_content = f.read()

    pattern = re.compile(
        r'(\d+)\s*\n(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*\n(.*?)(?=\n\s*\n|\Z)',
        re.DOTALL
    )
    matches = pattern.findall(srt_content)

    def srt_time_to_ass(t_str: str) -> str:
        t_str = t_str.replace(',', '.')
        parts = t_str.split(':')
        h = int(parts[0])
        m = parts[1]
        s_ms = parts[2]
        s, ms = s_ms.split('.')
        return f"{h}:{m}:{s}.{ms[:2]}"

    # 1080x1920 竖屏专属 ASS 配置：Alignment=5 居中置于视觉黄金中心
    ass_header = """[Script Info]
Title: Auto Media Subtitles
ScriptType: v4.00+
WrapStyle: 2
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Microsoft YaHei,50,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,2,0,1,3.5,2,5,80,80,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    events = []
    for idx, start, end, text in matches:
        start_ass = srt_time_to_ass(start.strip())
        end_ass = srt_time_to_ass(end.strip())
        clean_text = text.strip().replace('\r\n', ' ').replace('\n', ' ')
        wrapped_text = wrap_chinese_text(clean_text, max_chars=15)

        # 带有 120ms 的细腻平滑淡入淡出动效
        dialogue = f"Dialogue: 0,{start_ass},{end_ass},Default,,0,0,0,,{{\\fad(120,120)}}{wrapped_text}"
        events.append(dialogue)

    with open(ass_file, "w", encoding="utf-8") as f:
        f.write(ass_header + "\n".join(events) + "\n")

def render_video_with_ffmpeg(ffmpeg_path: str, audio_file: str, ass_file: str, output_video: str):
    """调用 FFmpeg 合成 1080x1920 竖屏黑底白字居中字幕视频"""
    print("\n[步骤 4/4] 正在使用 FFmpeg 渲染 1080x1920 竖屏高清成品视频...")
    
    ass_escaped = os.path.basename(ass_file)

    cmd = [
        ffmpeg_path,
        "-y",
        "-f", "lavfi",
        "-i", "color=c=0x111111:s=1080x1920:r=30",
        "-i", audio_file,
        "-vf", f"ass={ass_escaped}",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        output_video
    ]

    base_dir = os.path.dirname(os.path.abspath(output_video))
    result = subprocess.run(cmd, cwd=base_dir, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        print(f"\n[错误] FFmpeg 渲染失败:\n{result.stderr}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="自媒体全自动短视频合成工厂")
    parser.add_argument("--voice", help="指定音色: yunxi / xiaoxiao", default=None)
    parser.add_argument("--input", help="文案文件路径", default="今日文案.txt")
    parser.add_argument("--audio", help="输出音频路径", default="配音.mp3")
    parser.add_argument("--srt", help="输出字幕路径", default="字幕.srt")
    parser.add_argument("--ass", help="输出ASS字幕路径", default="字幕.ass")
    parser.add_argument("--output", help="输出视频路径", default="成品视频.mp4")
    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(base_dir, args.input) if not os.path.isabs(args.input) else args.input
    output_audio = os.path.join(base_dir, args.audio) if not os.path.isabs(args.audio) else args.audio
    output_srt = os.path.join(base_dir, args.srt) if not os.path.isabs(args.srt) else args.srt
    output_ass = os.path.join(base_dir, args.ass) if not os.path.isabs(args.ass) else args.ass
    output_video = os.path.join(base_dir, args.output) if not os.path.isabs(args.output) else args.output

    print("========================================================")
    print("      🎬 自媒体全自动短视频工厂 (1080x1920 竖屏版)")
    print("========================================================")

    # 1. 查找 FFmpeg
    ffmpeg_exe = find_ffmpeg()
    print(f">> FFmpeg 引擎已就绪: {os.path.basename(ffmpeg_exe)}")

    # 2. 读取文案
    text = load_text(input_path)
    clean_text = "".join(text.split())
    char_count = len(clean_text)
    print(f">> 已读取文案: 【{os.path.basename(input_path)}】 (共 {char_count} 字)")
    preview = clean_text[:45] + ("..." if len(clean_text) > 45 else "")
    print(f">> 内容预览: \"{preview}\"")

    # 3. 选择音色
    voice_id, voice_name = choose_voice(args.voice)
    print(f">> 当前选用: {voice_name}")

    # 4. 生成配音与字幕
    try:
        asyncio.run(generate_voice_and_subtitles(text, voice_id, output_audio, output_srt))
    except Exception as e:
        print(f"\n[错误] 配音生成失败: {e}")
        sys.exit(1)

    # 5. 转换字幕为居中动态 ASS
    print("\n[步骤 3/4] 正在优化居中动态字幕格式 (1080x1920 竖屏黄金居中)...")
    convert_srt_to_ass(output_srt, output_ass)

    # 6. 使用 FFmpeg 渲染成品视频
    render_video_with_ffmpeg(ffmpeg_exe, output_audio, output_ass, output_video)

    # 自动同步保存至 G:\矩阵短视频
    g_matrix_dir = r"G:\矩阵短视频"
    g_saved_path = None
    if os.path.exists("G:\\"):
        try:
            os.makedirs(g_matrix_dir, exist_ok=True)
            import shutil
            import datetime
            time_tag = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            g_latest = os.path.join(g_matrix_dir, "成品视频.mp4")
            g_archive = os.path.join(g_matrix_dir, f"矩阵短视频_{time_tag}.mp4")
            shutil.copy2(output_video, g_latest)
            shutil.copy2(output_video, g_archive)
            g_saved_path = g_latest
        except Exception as e:
            print(f"[!] 同步至 G 盘失败: {e}")

    # 7. 成果展示
    video_size_mb = os.path.getsize(output_video) / (1024 * 1024) if os.path.exists(output_video) else 0
    audio_size_kb = os.path.getsize(output_audio) / 1024 if os.path.exists(output_audio) else 0

    print("\n========================================================")
    print("   🎉 全部生成成功！零剪辑直接发抖音/快手/小红书/视频号")
    print("========================================================")
    print(f"   🎬 成品视频: {os.path.basename(output_video)} ({video_size_mb:.2f} MB, 1080x1920 竖屏)")
    if g_saved_path:
        print(f"   💾 矩阵短视频归档: {g_matrix_dir} (已同步保存最新版与历史版)")
    print(f"   🎵 纯音频轨: {os.path.basename(output_audio)} ({audio_size_kb:.1f} KB)")
    print(f"   💬 时间轴字幕: {os.path.basename(output_srt)} / {os.path.basename(output_ass)}")
    print(f"   📂 本地目录: {base_dir}")
    print("========================================================\n")

if __name__ == "__main__":
    main()
