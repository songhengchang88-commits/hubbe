# -*- coding: utf-8 -*-
"""
自媒体全自动配音与字幕生成工具
基于微软 edge-tts 引擎
"""

import os
import sys
import asyncio
import argparse

# 确保在 Windows 控制台下输出不会因为编码或字符集报错
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

    # 兼容多种编码读取
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
    """选择配音角色"""
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
        choice = input(">> 请输入数字序号选择 (直接按回车默认选 1 云希): ").strip()
    except (EOFError, KeyboardInterrupt):
        choice = "1"
    
    if not choice or choice not in VOICES:
        choice = "1"
    
    return VOICES[choice]

async def generate_with_retry(text: str, voice: str, output_audio: str, output_srt: str, max_retries: int = 3):
    """调用 edge-tts 生成音频与字幕，带超时保护与重试机制"""
    import edge_tts

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            retry_tag = f" (第 {attempt} 次尝试)" if attempt > 1 else ""
            print(f"\n[1/3] 正在连接微软云端语音引擎{retry_tag}...")
            communicate = edge_tts.Communicate(text, voice)
            submaker = edge_tts.SubMaker()
            
            print("[2/3] 正在合成高清配音并同步计算字幕时间轴...")
            audio_data = bytearray()

            async def _stream():
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_data.extend(chunk["data"])
                    elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                        submaker.feed(chunk)

            # 单次生成最长等待 30 秒，避免因网络僵死挂起
            await asyncio.wait_for(_stream(), timeout=30.0)

            # 写入音频
            with open(output_audio, "wb") as audio_file:
                audio_file.write(audio_data)

            # 写入字幕
            print("[3/3] 正在输出时间轴字幕文件...")
            srt_content = submaker.get_srt()
            with open(output_srt, "w", encoding="utf-8") as srt_file:
                srt_file.write(srt_content)

            return  # 成功完成
        except (asyncio.TimeoutError, Exception) as e:
            last_error = e
            if attempt < max_retries:
                print(f"[!] 网络连接出现波动 ({e})，2 秒后自动重新尝试...")
                await asyncio.sleep(2)
            else:
                raise last_error

def main():
    parser = argparse.ArgumentParser(description="自媒体全自动配音与字幕生成器")
    parser.add_argument("--voice", help="指定音色: yunxi / xiaoxiao", default=None)
    parser.add_argument("--input", help="文案文件路径", default="今日文案.txt")
    parser.add_argument("--audio", help="输出音频路径", default="配音.mp3")
    parser.add_argument("--srt", help="输出字幕路径", default="字幕.srt")
    args = parser.parse_args()

    # 脚本所在目录
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(base_dir, args.input) if not os.path.isabs(args.input) else args.input
    output_audio = os.path.join(base_dir, args.audio) if not os.path.isabs(args.audio) else args.audio
    output_srt = os.path.join(base_dir, args.srt) if not os.path.isabs(args.srt) else args.srt

    print("========================================================")
    print("        自媒体全自动配音 & 字幕生成器 v1.0")
    print("========================================================")

    # 1. 加载文案
    text = load_text(input_path)
    clean_text = "".join(text.split())
    char_count = len(clean_text)
    print(f"\n>> 已读取文案: 【{os.path.basename(input_path)}】")
    print(f">> 文案净字数: {char_count} 字")
    preview = clean_text[:45] + ("..." if len(clean_text) > 45 else "")
    print(f">> 内容预览: \"{preview}\"")

    # 2. 选择音色
    voice_id, voice_name = choose_voice(args.voice)
    print(f"\n>> 当前选用: {voice_name}")

    # 3. 生成配音与字幕
    try:
        asyncio.run(generate_with_retry(text, voice_id, output_audio, output_srt))
    except Exception as e:
        print(f"\n[错误] 生成失败: {e}")
        print("\n【排查指南】")
        print("1. 请检查您的电脑网络是否能正常访问网络；")
        print("2. 如开启了系统级代理或某些VPN软件，可尝试关闭后再试。")
        sys.exit(1)

    # 4. 统计结果展示
    audio_size_kb = os.path.getsize(output_audio) / 1024 if os.path.exists(output_audio) else 0
    print("\n========================================================")
    print("   [√] 全部生成成功！可直接导入剪映/PR等视频剪辑软件")
    print("========================================================")
    print(f"   [音频文件] {os.path.basename(output_audio)} ({audio_size_kb:.1f} KB)")
    print(f"   [字幕文件] {os.path.basename(output_srt)}")
    print(f"   [存放位置] {base_dir}")
    print("========================================================\n")

if __name__ == "__main__":
    main()
