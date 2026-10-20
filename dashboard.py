# -*- coding: utf-8 -*-
"""
自媒体全自动工厂 - 全球多平台矩阵总控台 (v5.0 旗舰动态 AI 控制台)
适配平台：小红书 + X (Twitter) + Instagram + YouTube Shorts (已停用微信视频号)
特色：
1. 现代化 Obsidian Cyber 深空发光科技界面 (无黑框启动)
2. 动态精准时钟与每晚 23:00 全球矩阵定时发布倒计时
3. 真实视频路径全景监控：实时显示当前即将发布的切片文件绝对路径与配套文案
4. 深度打通 G:\矩阵短视频 三级目录资产库 (待切片视频 / 已完成切片\日期 / 已发布归档)
5. 4大平台独立一键免扫码/免密浏览器配置接入
"""

import os
import sys
import re
import shutil
import time
import json
import glob
import datetime
import threading
import subprocess
import webbrowser
import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox, ttk

# 颜色系统定义
C_BG_DARK = "#0d1117"        # 深空黑曜石底色
C_CARD_BG = "#161f2e"        # 玻璃态卡片背景
C_CARD_BORDER = "#253347"    # 边框科技蓝
C_CYAN = "#00f2fe"           # 发光青蓝 (主高光)
C_GREEN = "#10b981"          # 荧光绿 (运行/成功状态)
C_AMBER = "#f59e0b"          # 琥珀橙 (警告/倒计时)
C_RED = "#ef4444"            # 霓虹红 (忙碌/错误)
C_PURPLE = "#a855f7"         # 幻彩紫 (AI 特性)
C_TEXT_LIGHT = "#f1f5f9"     # 标题正白
C_TEXT_MUTED = "#94a3b8"     # 辅助灰白

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "browser_data")
G_BASE = r"G:\矩阵短视频" if os.path.exists("G:\\") else BASE_DIR

DIR_PENDING = os.path.join(G_BASE, "待切片视频")
DIR_COMPLETED = os.path.join(G_BASE, "已完成切片")
DIR_PUBLISHED = os.path.join(G_BASE, "已发布")
RECORD_FILE = os.path.join(DIR_PUBLISHED, "published_record.json")

os.makedirs(DATA_DIR, exist_ok=True)

os.makedirs(DIR_PENDING, exist_ok=True)
os.makedirs(DIR_COMPLETED, exist_ok=True)
os.makedirs(DIR_PUBLISHED, exist_ok=True)

class MediaFactoryDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("🎬 自媒体全自动工厂 | 全球多平台矩阵 AI 超级总控台")
        self.root.geometry("1240x860")
        self.root.minsize(1040, 720)
        self.root.configure(bg=C_BG_DARK)

        self.selected_video_path = ""
        self.is_running = False

        self._build_header()
        self._build_body()
        self._start_dynamic_clock()
        self._refresh_slice_path_monitor()

    def _build_header(self):
        """顶部发光标题栏与全局监控胶囊"""
        header_frame = tk.Frame(self.root, bg=C_BG_DARK)
        header_frame.pack(fill=tk.X, padx=16, pady=(10, 4))

        # 标题与副标题区
        title_box = tk.Frame(header_frame, bg=C_BG_DARK)
        title_box.pack(side=tk.LEFT)

        lbl_logo = tk.Label(
            title_box,
            text="⚡ 自媒体全自动工厂 · 全球矩阵发布总控",
            font=("微软雅黑", 15, "bold"),
            bg=C_BG_DARK,
            fg=C_CYAN
        )
        lbl_logo.pack(anchor="w")

        lbl_sub = tk.Label(
            title_box,
            text="24h 无人值守短视频流水线 · 智能切片 · 影视解说 · 小红书/X/IG/YouTube 每日23:00自动发布",
            font=("微软雅黑", 8),
            bg=C_BG_DARK,
            fg=C_TEXT_MUTED
        )
        lbl_sub.pack(anchor="w")

        # 状态胶囊卡片（右侧）
        pills_box = tk.Frame(header_frame, bg=C_BG_DARK)
        pills_box.pack(side=tk.RIGHT)

        self.clock_label = tk.Label(
            pills_box,
            text="🕒 2026-10-18 23:00:00",
            font=("Consolas", 9, "bold"),
            bg=C_CARD_BG,
            fg=C_TEXT_LIGHT,
            padx=10,
            pady=4,
            relief=tk.FLAT
        )
        self.clock_label.pack(side=tk.RIGHT, padx=4)

        self.schedule_pill = tk.Label(
            pills_box,
            text="⏰ 定时发布: 每天 23:00 (自动发 2 条)",
            font=("微软雅黑", 9, "bold"),
            bg="#2a1f05",
            fg=C_AMBER,
            padx=10,
            pady=4,
            relief=tk.FLAT
        )
        self.schedule_pill.pack(side=tk.RIGHT, padx=4)

        self.engine_pill = tk.Label(
            pills_box,
            text="● 矩阵就绪",
            font=("微软雅黑", 9, "bold"),
            bg="#062e20",
            fg=C_GREEN,
            padx=10,
            pady=4,
            relief=tk.FLAT
        )
        self.engine_pill.pack(side=tk.RIGHT, padx=4)

    def _build_body(self):
        """主体分栏框架（左侧操作卡片群，右侧实时控制台）"""
        main_frame = tk.Frame(self.root, bg=C_BG_DARK)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=6)

        # =========================================================================
        # 左侧控制面板（卡片群）
        # =========================================================================
        left_container = tk.Frame(main_frame, bg=C_BG_DARK)
        left_container.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        # Card 1: 🎞️ 视频素材获取与导入
        card1 = self._create_card(left_container, "📥 步骤一：长视频素材获取与导入")
        
        url_frame = tk.Frame(card1, bg=C_CARD_BG)
        url_frame.pack(fill=tk.X, padx=8, pady=3)

        self.url_entry = tk.Entry(
            url_frame,
            font=("Consolas", 9),
            bg="#0a0f18",
            fg=C_TEXT_LIGHT,
            insertbackground="white",
            relief=tk.SOLID,
            bd=1
        )
        self.url_entry.insert(0, "粘贴 B站/抖音/YouTube/M3U8直链...")
        self.url_entry.bind("<FocusIn>", self._on_url_focus_in)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)

        btn_dl = tk.Button(
            url_frame,
            text="⬇️ 一键下载",
            font=("微软雅黑", 8, "bold"),
            bg="#0284c7",
            fg="white",
            cursor="hand2",
            relief=tk.FLAT,
            command=self.download_url_video
        )
        btn_dl.pack(side=tk.RIGHT, padx=(4, 0))

        row1 = tk.Frame(card1, bg=C_CARD_BG)
        row1.pack(fill=tk.X, padx=8, pady=2)
        tk.Button(row1, text="📁 选取电脑视频原片", font=("微软雅黑", 8), bg="#1e293b", fg="white", relief=tk.FLAT, cursor="hand2", command=self.choose_local_video).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        tk.Button(row1, text="🎯 官方电影示范片", font=("微软雅黑", 8), bg="#1e293b", fg="#fde047", relief=tk.FLAT, cursor="hand2", command=self.download_demo_sample).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)

        row2 = tk.Frame(card1, bg=C_CARD_BG)
        row2.pack(fill=tk.X, padx=8, pady=2)
        tk.Button(row2, text="🐱 打开 Edge 安装猫抓", font=("微软雅黑", 8, "bold"), bg="#c2410c", fg="white", relief=tk.FLAT, cursor="hand2", command=self.open_cat_catch_store).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        tk.Button(row2, text="📥 导入浏览器最新下载", font=("微软雅黑", 8), bg="#0f766e", fg="white", relief=tk.FLAT, cursor="hand2", command=self.import_latest_from_downloads).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)

        self.selected_label = tk.Label(
            card1,
            text="当前源: 【待切片视频】素材库最新文件",
            font=("微软雅黑", 8),
            bg=C_CARD_BG,
            fg=C_CYAN,
            anchor="w"
        )
        self.selected_label.pack(fill=tk.X, padx=8, pady=(2, 4))

        # Card 2: ⚡ 工业级智能切片引擎
        card2 = self._create_card(left_container, "⚡ 步骤二：工业级智能切片引擎 (存入日期切片库)")

        # AI 增强功能开关行
        opt_box = tk.Frame(card2, bg=C_CARD_BG)
        opt_box.pack(fill=tk.X, padx=6, pady=2)

        self.var_scenedetect = tk.BooleanVar(value=True)
        self.var_mediapipe = tk.BooleanVar(value=True)
        self.var_autoeditor = tk.BooleanVar(value=True)
        self.var_trim_intro_outro = tk.BooleanVar(value=True)

        tk.Checkbutton(opt_box, text="分镜吸附", variable=self.var_scenedetect, font=("微软雅黑", 8), bg=C_CARD_BG, fg=C_CYAN, selectcolor="#0d1117", activebackground=C_CARD_BG, activeforeground=C_CYAN).pack(side=tk.LEFT, padx=1)
        tk.Checkbutton(opt_box, text="人脸C位", variable=self.var_mediapipe, font=("微软雅黑", 8), bg=C_CARD_BG, fg=C_CYAN, selectcolor="#0d1117", activebackground=C_CARD_BG, activeforeground=C_CYAN).pack(side=tk.LEFT, padx=1)
        tk.Checkbutton(opt_box, text="无声提速", variable=self.var_autoeditor, font=("微软雅黑", 8), bg=C_CARD_BG, fg=C_CYAN, selectcolor="#0d1117", activebackground=C_CARD_BG, activeforeground=C_CYAN).pack(side=tk.LEFT, padx=1)
        tk.Checkbutton(opt_box, text="去头去尾", variable=self.var_trim_intro_outro, font=("微软雅黑", 8), bg=C_CARD_BG, fg=C_CYAN, selectcolor="#0d1117", activebackground=C_CARD_BG, activeforeground=C_CYAN).pack(side=tk.LEFT, padx=1)

        # 切片时长选择行 (默认 5分钟)
        dur_box = tk.Frame(card2, bg=C_CARD_BG)
        dur_box.pack(fill=tk.X, padx=6, pady=(1, 3))
        
        lbl_dur = tk.Label(dur_box, text="⏱️ 切片时长:", font=("微软雅黑", 8, "bold"), bg=C_CARD_BG, fg=C_AMBER)
        lbl_dur.pack(side=tk.LEFT, padx=(2, 4))
        
        self.var_duration = tk.IntVar(value=300) # 默认 300 秒 (5分钟左右)
        
        tk.Radiobutton(dur_box, text="1分钟短视频", variable=self.var_duration, value=60, font=("微软雅黑", 8), bg=C_CARD_BG, fg=C_TEXT_LIGHT, selectcolor="#0d1117", activebackground=C_CARD_BG).pack(side=tk.LEFT, padx=2)
        tk.Radiobutton(dur_box, text="3分钟精选", variable=self.var_duration, value=180, font=("微软雅黑", 8), bg=C_CARD_BG, fg=C_TEXT_LIGHT, selectcolor="#0d1117", activebackground=C_CARD_BG).pack(side=tk.LEFT, padx=2)
        tk.Radiobutton(dur_box, text="🎬 5分钟解说", variable=self.var_duration, value=300, font=("微软雅黑", 8, "bold"), bg=C_CARD_BG, fg=C_CYAN, selectcolor="#0d1117", activebackground=C_CARD_BG).pack(side=tk.LEFT, padx=2)

        tk.Button(
            card2,
            text="1️⃣ 抓取最新爆款影视选题",
            font=("微软雅黑", 9),
            bg="#0284c7",
            fg="white",
            relief=tk.FLAT,
            cursor="hand2",
            command=lambda: self.run_task("抓取选题", "4_抓取欧乐热门影视并生成选题.bat")
        ).pack(fill=tk.X, padx=8, pady=2)

        tk.Button(
            card2,
            text="2️⃣ 开始智能长视频切片与出片\n(AI对齐 + 人脸C位 + 去头尾 + 智能5分钟解说长切片)",
            font=("微软雅黑", 9, "bold"),
            bg="#0369a1",
            fg="white",
            relief=tk.FLAT,
            cursor="hand2",
            height=2,
            command=self.run_slicing_task
        ).pack(fill=tk.X, padx=8, pady=3)

        # Card 3: 🚀 全球矩阵自动发布 (小红书/X/Instagram/YouTube)
        card3 = self._create_card(left_container, "🚀 步骤三：全球矩阵发布 (小红书/X/IG/YouTube)")

        # 实时待发布视频路径监测面板
        self.next_slice_frame = tk.Frame(card3, bg="#0d1726", bd=1, relief=tk.SOLID)
        self.next_slice_frame.pack(fill=tk.X, padx=8, pady=2)

        self.next_slice_label = tk.Label(
            self.next_slice_frame,
            text="🎯 正在精准监测待发布切片路径...",
            font=("微软雅黑", 8, "bold"),
            bg="#0d1726",
            fg="#38bdf8",
            anchor="w",
            justify=tk.LEFT,
            wraplength=380
        )
        self.next_slice_label.pack(fill=tk.X, padx=6, pady=3)

        # 核心发布按钮
        tk.Button(
            card3,
            text="🚀 一键发布切片至全矩阵\n(小红书 + 抖音 + YouTube Shorts + Instagram [X已停用])",
            font=("微软雅黑", 10, "bold"),
            bg="#15803d",
            fg="white",
            relief=tk.FLAT,
            cursor="hand2",
            height=2,
            command=self.run_matrix_publish_now
        ).pack(fill=tk.X, padx=8, pady=2)

        tk.Button(
            card3,
            text="⏰ 立即执行一次夜间 23:00 矩阵发布测试\n(精准读取切片库，发布后自动归档到已发布)",
            font=("微软雅黑", 8, "bold"),
            bg="#854d0e",
            fg="white",
            relief=tk.FLAT,
            cursor="hand2",
            command=self.run_matrix_publish_now
        ).pack(fill=tk.X, padx=8, pady=3)

        # 5大平台免密免扫码配置入口
        tk.Button(
            card3,
            text="🌐 打开【自媒体专用内置登录浏览器】\n(在内置独立应用窗口中直接登录，绝不闪退，自动永久保存)",
            font=("微软雅黑", 9, "bold"),
            bg="#0284c7",
            fg="white",
            relief=tk.FLAT,
            cursor="hand2",
            height=2,
            command=self.open_builtin_browser_hub
        ).pack(fill=tk.X, padx=8, pady=(4, 4))

        lbl_login_title = tk.Label(
            card3,
            text="🔑 快速启动单平台内置应用浏览器 (直接扫码/密码登录):",
            font=("微软雅黑", 8, "bold"),
            bg=C_CARD_BG,
            fg=C_AMBER,
            anchor="w"
        )
        lbl_login_title.pack(fill=tk.X, padx=8, pady=(2, 1))

        plat_row1 = tk.Frame(card3, bg=C_CARD_BG)
        plat_row1.pack(fill=tk.X, padx=8, pady=1)
        tk.Button(plat_row1, text="📕 小红书内置登录", font=("微软雅黑", 8), bg="#be123c", fg="white", relief=tk.FLAT, cursor="hand2", command=lambda: self.launch_platform_login("xiaohongshu")).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        tk.Button(plat_row1, text="🎵 抖音内置登录", font=("微软雅黑", 8, "bold"), bg="#1e1b4b", fg="#38bdf8", relief=tk.FLAT, cursor="hand2", command=lambda: self.launch_platform_login("douyin")).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)

        plat_row2 = tk.Frame(card3, bg=C_CARD_BG)
        plat_row2.pack(fill=tk.X, padx=8, pady=1)
        tk.Button(plat_row2, text="🎬 YouTube 登录", font=("微软雅黑", 8), bg="#b91c1c", fg="white", relief=tk.FLAT, cursor="hand2", command=lambda: self.launch_platform_login("youtube")).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        tk.Button(plat_row2, text="📸 Instagram 登录", font=("微软雅黑", 8), bg="#7e22ce", fg="white", relief=tk.FLAT, cursor="hand2", command=lambda: self.launch_platform_login("ig")).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        tk.Button(plat_row2, text="✖️ X 申诉", font=("微软雅黑", 8), bg="#1e293b", fg="#94a3b8", relief=tk.FLAT, cursor="hand2", command=lambda: self.launch_platform_login("x")).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)

        # Card 4: 📂 G 盘矩阵资产目录管理
        card4 = self._create_card(left_container, "📂 G 盘矩阵资产与成果管理")
        
        g_row1 = tk.Frame(card4, bg=C_CARD_BG)
        g_row1.pack(fill=tk.X, padx=8, pady=2)
        tk.Button(g_row1, text="📂 待切片视频", font=("微软雅黑", 8), bg="#334155", fg="white", relief=tk.FLAT, cursor="hand2", command=lambda: self.open_dir(DIR_PENDING)).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        tk.Button(g_row1, text="📂 今日已完成切片", font=("微软雅黑", 8, "bold"), bg="#1e3a8a", fg="white", relief=tk.FLAT, cursor="hand2", command=self.open_today_completed_dir).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        tk.Button(g_row1, text="📂 已发布归档", font=("微软雅黑", 8), bg="#065f46", fg="white", relief=tk.FLAT, cursor="hand2", command=lambda: self.open_dir(DIR_PUBLISHED)).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)

        g_row2 = tk.Frame(card4, bg=C_CARD_BG)
        g_row2.pack(fill=tk.X, padx=8, pady=(1, 4))
        tk.Button(g_row2, text="📄 今日爆款选题表", font=("微软雅黑", 8), bg="#1e293b", fg="white", relief=tk.FLAT, cursor="hand2", command=self.open_topics_file).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        tk.Button(g_row2, text="🔄 刷新切片监测", font=("微软雅黑", 8), bg="#1e293b", fg=C_CYAN, relief=tk.FLAT, cursor="hand2", command=self._refresh_slice_path_monitor).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        tk.Button(g_row2, text="🧹 清空日志", font=("微软雅黑", 8), bg="#1e293b", fg=C_TEXT_MUTED, relief=tk.FLAT, cursor="hand2", command=self.clear_log).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)

        # =========================================================================
        # 右侧动态 Live Console (AI 极客控制台)
        # =========================================================================
        log_frame = tk.Frame(main_frame, bg=C_CARD_BG, relief=tk.SOLID, bd=1)
        log_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        console_bar = tk.Frame(log_frame, bg="#111827")
        console_bar.pack(fill=tk.X, padx=6, pady=4)

        tk.Label(
            console_bar,
            text="🖥️ 实时工作动态与 AI 任务监控 (Live Console)",
            font=("Consolas", 10, "bold"),
            bg="#111827",
            fg=C_CYAN
        ).pack(side=tk.LEFT)

        self.running_status = tk.Label(
            console_bar,
            text="● IDLE (待命)",
            font=("Consolas", 9),
            bg="#111827",
            fg=C_GREEN
        )
        self.running_status.pack(side=tk.RIGHT)

        # 1. 动态切片与任务进度条容器 (Cyber 风格)
        self.progress_frame = tk.Frame(log_frame, bg="#111827", bd=1, relief=tk.SOLID)
        self.progress_frame.pack(fill=tk.X, padx=6, pady=(0, 2))

        prog_top = tk.Frame(self.progress_frame, bg="#111827")
        prog_top.pack(fill=tk.X, padx=6, pady=(2, 1))

        tk.Label(
            prog_top,
            text="⚡ AI 切片与流水线进度:",
            font=("微软雅黑", 8, "bold"),
            bg="#111827",
            fg=C_CYAN
        ).pack(side=tk.LEFT)

        self.lbl_progress_percent = tk.Label(
            prog_top,
            text="0% [待命中]",
            font=("Consolas", 8, "bold"),
            bg="#111827",
            fg=C_TEXT_MUTED
        )
        self.lbl_progress_percent.pack(side=tk.RIGHT)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Cyber.Horizontal.TProgressbar",
                        troughcolor='#0a0f18',
                        bordercolor='#253347',
                        background='#00f2fe',
                        lightcolor='#00f2fe',
                        darkcolor='#00f2fe')

        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            style="Cyber.Horizontal.TProgressbar",
            orient="horizontal",
            length=400,
            mode="determinate"
        )
        self.progress_bar.pack(fill=tk.X, padx=6, pady=(1, 3))

        # 2. 全平台发布实时状态看板 (成功 / 失败 / 未成功状态指示)
        self.status_bar_frame = tk.Frame(log_frame, bg="#0d1726", bd=1, relief=tk.SOLID)
        self.status_bar_frame.pack(fill=tk.X, padx=6, pady=(0, 4))

        tk.Label(
            self.status_bar_frame,
            text="📊 矩阵发布状态:",
            font=("微软雅黑", 8, "bold"),
            bg="#0d1726",
            fg=C_TEXT_LIGHT
        ).pack(side=tk.LEFT, padx=(6, 4), pady=3)

        self.platform_badges = {}
        badge_configs = [
            ("xiaohongshu", "📕 小红书", C_TEXT_MUTED),
            ("douyin", "🎵 抖音", C_TEXT_MUTED),
            ("youtube", "🎬 YouTube", C_TEXT_MUTED),
            ("instagram", "📸 Instagram", C_TEXT_MUTED)
        ]
        for key, name, def_col in badge_configs:
            lbl = tk.Label(
                self.status_bar_frame,
                text=f"{name}: 【待命】",
                font=("微软雅黑", 8, "bold"),
                bg="#161f2e",
                fg=def_col,
                padx=6,
                pady=2,
                relief=tk.FLAT
            )
            lbl.pack(side=tk.LEFT, padx=2, pady=2)
            self.platform_badges[key] = lbl

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            font=("Consolas", 10),
            bg="#080c14",
            fg="#00ff88",
            insertbackground="white",
            relief=tk.FLAT,
            bd=0
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

        self.log("================================================================================")
        self.log("【系统就绪】自媒体全自动工厂 - 全球多平台矩阵总控台 (v5.0 旗舰动态 AI 版) 已启动！")
        self.log(f">> 待切片素材池: {DIR_PENDING}")
        self.log(f">> 每日切片完成库: {DIR_COMPLETED}\\YYYY-MM-DD")
        self.log(f">> 已发布归档库: {DIR_PUBLISHED}")
        self.log("【发布通道调整通知】")
        self.log(" 🌟 [已按照指令完全停用微信视频号]")
        self.log(" 🌟 [已全面切换发布目标至: 小红书 + X (Twitter) + Instagram + YouTube Shorts]")
        self.log(" 🌟 [精准视频路径发现已激活] 自动检索【已完成切片】各日期文件夹并绑定配套文案")
        self.log(" 🌟 [夜间23:00计划任务已同步更新] Windows 计划任务 MediaFactory_Matrix_Publish_2300 已就绪")
        self.log("================================================================================\n")

    def _create_card(self, parent, title_text):
        card = tk.LabelFrame(
            parent,
            text=f" {title_text} ",
            font=("微软雅黑", 9, "bold"),
            bg=C_CARD_BG,
            fg=C_CYAN,
            bd=1,
            relief=tk.SOLID
        )
        card.pack(fill=tk.X, pady=2, ipadx=2)
        return card

    def _refresh_slice_path_monitor(self):
        """实时扫描 G 盘切片库并更新待发布切片路径展示"""
        try:
            from publish_multi_platform import get_pending_slices
            slices = get_pending_slices(max_count=2)
            if slices:
                first = slices[0]
                total_slices = len(glob.glob(os.path.join(DIR_COMPLETED, "*", "*.mp4")))
                self.next_slice_label.config(
                    text=f"🎯 下一部待发布切片 (共 {total_slices} 部未发):\n"
                         f"📄 文件: {first['filename']}\n"
                         f"📁 路径: {first['path']}\n"
                         f"🏷️ 标题: {first['title'][:22]}...",
                    fg="#38bdf8"
                )
            else:
                self.next_slice_label.config(
                    text="🎯 切片库状态: 暂无待发布新切片 (请在上方点击【2️⃣ 智能长视频切片】制作)",
                    fg=C_AMBER
                )
        except Exception as e:
            self.next_slice_label.config(text=f"切片监测信息: {e}", fg=C_TEXT_MUTED)

        # 30秒自检一次
        self.root.after(30000, self._refresh_slice_path_monitor)

    def _start_dynamic_clock(self):
        """实时更新时钟与夜间 23:00 倒计时"""
        now = datetime.datetime.now()
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")

        target_time = now.replace(hour=23, minute=0, second=0, microsecond=0)
        if now > target_time:
            target_time += datetime.timedelta(days=1)
        diff = target_time - now
        hours, remainder = divmod(int(diff.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        countdown_str = f"倒计时 {hours:02d}:{minutes:02d}:{seconds:02d}"

        self.clock_label.config(text=f"🕒 {now_str}")
        self.schedule_pill.config(text=f"⏰ 23:00 全球矩阵发布 ({countdown_str})")

        self.root.after(1000, self._start_dynamic_clock)

    def log(self, message):
        def _append():
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
        self.root.after(0, _append)

    def set_status(self, text, color=C_GREEN):
        def _update():
            self.running_status.config(text=text, fg=color)
        self.root.after(0, _update)

    def update_progress(self, percent: int, desc: str):
        """更新 AI 切片与流水线进度条与状态文字"""
        def _do():
            self.progress_bar["value"] = percent
            self.lbl_progress_percent.config(text=f"{percent}% [{desc}]")
            if percent >= 100:
                self.lbl_progress_percent.config(fg=C_GREEN)
            elif percent > 0:
                self.lbl_progress_percent.config(fg=C_CYAN)
            else:
                self.lbl_progress_percent.config(fg=C_TEXT_MUTED)
        self.root.after(0, _do)

    def update_platform_status(self, platform_name: str, status_text: str, color: str):
        """更新控制台界面上的各平台发布实时反馈徽章"""
        def _do():
            p_lower = platform_name.lower()
            key_map = {
                "小红书": "xiaohongshu", "red": "xiaohongshu", "xhs": "xiaohongshu",
                "抖音": "douyin", "dy": "douyin",
                "youtube": "youtube", "yt": "youtube",
                "instagram": "instagram", "ig": "instagram"
            }
            matched_key = None
            for alias, k in key_map.items():
                if alias in p_lower:
                    matched_key = k
                    break

            if matched_key and matched_key in self.platform_badges:
                lbl = self.platform_badges[matched_key]
                prefix = lbl.cget("text").split(":")[0]
                lbl.config(text=f"{prefix}: {status_text}", fg=color)
        self.root.after(0, _do)

    def _parse_live_line(self, line: str):
        """解析命令行输出流中的阶段进度与发布状态"""
        # 1. 匹配进度百分比
        m_prog = re.search(r"\[进度\s*(\d+)%\]\s*(.*)", line)
        if m_prog:
            pct = int(m_prog.group(1))
            desc = m_prog.group(2).strip()
            self.update_progress(pct, desc)
        elif "提取高保真语音音轨" in line:
            self.update_progress(10, "提取音轨中")
        elif "AI 语音对齐模型" in line or "语音识别与分词" in line:
            self.update_progress(25, "Whisper 语音转录中")
        elif "语言语义边界切分" in line:
            self.update_progress(40, "语义高光切分中")
        elif "PySceneDetect" in line or "镜头" in line:
            self.update_progress(55, "分镜防截断吸附中")
        elif "MediaPipe" in line:
            self.update_progress(65, "人脸黄金居中计算中")
        elif "正在渲染" in line or "Filter Graph" in line:
            self.update_progress(75, "FFmpeg 竖屏高清压制")
        elif "auto-editor" in line or "冗余停顿" in line:
            self.update_progress(90, "无声冗余智能剔除")
        elif "全套切片流水线执行完毕" in line or "长视频切片成果" in line:
            self.update_progress(100, "切片完成已入库")

        # 2. 匹配平台发布状态
        m_plat = re.search(r"\[平台状态\]\s*(.*?):\s*(.*)", line)
        if m_plat:
            plat_name = m_plat.group(1).strip()
            stat_text = m_plat.group(2).strip()
            if "✅" in stat_text or "成功" in stat_text:
                color = C_GREEN
            elif "发布中" in stat_text:
                color = C_AMBER
            elif "❌" in stat_text or "未成功" in stat_text:
                color = C_RED
            else:
                color = C_TEXT_MUTED
            self.update_platform_status(plat_name, stat_text, color)

    def _on_url_focus_in(self, event):
        if "粘贴" in self.url_entry.get():
            self.url_entry.delete(0, tk.END)

    def clear_log(self):
        self.log_text.delete("1.0", tk.END)
        self.log(">> 控制台日志已清空。\n")

    def open_browser(self, url):
        self.log(f"[浏览器] 正在为您打开网页入口: {url}")
        webbrowser.open(url)

    def open_dir(self, target_dir):
        if not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)
        os.system(f'explorer.exe "{target_dir}"')
        self.log(f">> 已在资源管理器中打开文件夹: {target_dir}")

    def open_today_completed_dir(self):
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        daily_dir = os.path.join(DIR_COMPLETED, today_str)
        self.open_dir(daily_dir)

    def open_topics_file(self):
        txt_path = os.path.join(BASE_DIR, "今日爆款影视选题表.txt")
        if os.path.exists(txt_path):
            os.system(f'start notepad.exe "{txt_path}"')
            self.log(f">> 已使用记事本打开选题表: {txt_path}")
        else:
            self.log(f"[提示] 尚未生成《今日爆款影视选题表.txt》，请先点击【1️⃣ 抓取最新爆款影视选题】！")

    def open_cat_catch_store(self):
        url = "https://microsoftedge.microsoft.com/addons/detail/%E7%8C%AB%E6%8A%93/oikmmpeloialedfljfdakflbejmpakde"
        webbrowser.open(url)
        self.log("\n[猫抓嗅探] 已在 Edge 浏览器中打开【猫抓】扩展安装页面！")

    def open_builtin_browser_hub(self):
        """打开内置多平台登录浏览器管理总控"""
        py_exe = sys.executable
        if os.path.exists(r"C:\Program Files\Python311\python.exe"):
            py_exe = r"C:\Program Files\Python311\python.exe"
        cmd = [py_exe, os.path.join(BASE_DIR, "builtin_browser.py")]
        subprocess.Popen(cmd)
        self.log("\n[内置浏览器] 已启动【自媒体内置登录浏览器管理中心】！")
        self.log("👉 您可以在独立的内置应用窗口中自由选择平台进行扫码或密码登录，登录后自动永久保存凭证！\n")

    def launch_platform_login(self, platform_key):
        """直接以专属内置独立应用窗口启动指定平台登录"""
        from builtin_browser import PLATFORMS_CONFIG, find_edge_exe, check_login_status
        edge_exe = find_edge_exe()

        cfg_map = {
            "xiaohongshu": PLATFORMS_CONFIG[0],
            "x": PLATFORMS_CONFIG[1],
            "twitter_x": PLATFORMS_CONFIG[1],
            "ig": PLATFORMS_CONFIG[2],
            "instagram": PLATFORMS_CONFIG[2],
            "youtube": PLATFORMS_CONFIG[3],
            "douyin": PLATFORMS_CONFIG[4]
        }
        cfg = cfg_map.get(platform_key, PLATFORMS_CONFIG[0])
        profile_dir = os.path.join(DATA_DIR, cfg["folder"])
        os.makedirs(profile_dir, exist_ok=True)

        self.log(f"\n[内置应用浏览器] 正在启动【{cfg['name']}】专属内置窗口...")
        self.log(f">> 目标页面: {cfg['url']}")
        self.log(f">> 登录状态与 Cookie 保存路径: {profile_dir}")
        self.log(f"👉 提示：{cfg['guide']}")
        self.log("👉 窗口已保持开启，请直接在弹出的内置窗口中完成登录，关闭后凭证自动永久写入！\n")

        cmd = [
            edge_exe,
            f"--user-data-dir={profile_dir}",
            f"--app={cfg['url']}",
            "--window-size=1200,850",
            "--disable-blink-features=AutomationControlled",
            "--no-first-run",
            "--no-default-browser-check"
        ]

        def runner():
            try:
                proc = subprocess.Popen(cmd)
                proc.wait()
                is_ok, msg = check_login_status(cfg)
                self.log(f"\n[内置浏览器] 【{cfg['name']}】窗口已关闭！")
                self.log(f">> 凭证检测结果: {msg}")
                self.log(">> 登录数据已永久保存在本地，矩阵发布时将自动免密调用！\n")
            except Exception as e:
                self.log(f"[!] 启动内置浏览器异常: {e}")

        threading.Thread(target=runner, daemon=True).start()

    def import_latest_from_downloads(self):
        downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        if not os.path.exists(downloads_dir):
            messagebox.showinfo("提示", "未找到系统的【下载】文件夹！")
            return
        
        exts = (".mp4", ".mkv", ".mov", ".flv", ".avi", ".webm")
        files = [os.path.join(downloads_dir, f) for f in os.listdir(downloads_dir) if f.lower().endswith(exts)]
        if not files:
            self.log("[提示] 系统的【下载】文件夹中暂无新的视频，请先在网页猫抓中点击下载！")
            return
        
        latest_file = max(files, key=os.path.getmtime)
        dest_file = os.path.join(DIR_PENDING, os.path.basename(latest_file))
        try:
            shutil.copy2(latest_file, dest_file)
            self.selected_video_path = dest_file
            name = os.path.basename(dest_file)
            self.selected_label.config(text=f"当前指定源: 【{name}】", fg=C_CYAN)
            self.log(f">> 成功导入浏览器下载的最新影视视频: {dest_file}")
            self.log(">> 现在直接点击【2️⃣ 开始智能长视频切片与出片】即可一键出片！\n")
        except Exception as e:
            self.log(f"[!] 导入失败: {e}")

    def choose_local_video(self):
        file_path = filedialog.askopenfilename(
            title="选择要进行 AI 切片的本地长视频",
            initialdir=DIR_PENDING,
            filetypes=[("视频文件", "*.mp4 *.mkv *.mov *.avi *.flv *.webm"), ("所有文件", "*.*")]
        )
        if file_path:
            self.selected_video_path = file_path
            name = os.path.basename(file_path)
            self.selected_label.config(text=f"当前指定源: 【{name}】", fg=C_CYAN)
            self.log(f">> 已选定长视频原片: {file_path}")

    def download_url_video(self):
        url = self.url_entry.get().strip()
        if not url or "粘贴" in url:
            messagebox.showinfo("提示", "请先在输入框中粘贴有效的视频链接！")
            return

        def dl_worker():
            self.set_status("● 正在下载视频素材...", C_AMBER)
            self.log(f"\n[素材下载] 开始解析并下载在线视频: {url}")
            from download_video_resource import download_online_video
            res = download_online_video(url)
            if res and os.path.exists(res):
                self.selected_video_path = res
                name = os.path.basename(res)
                self.root.after(0, lambda: self.selected_label.config(text=f"当前指定源: 【{name}】", fg=C_CYAN))
                self.log(f"\n[素材就绪] 视频已下载成功！文件路径: {res}\n")
            self.set_status("● IDLE (待命)", C_GREEN)

        threading.Thread(target=dl_worker, daemon=True).start()

    def download_demo_sample(self):
        def demo_worker():
            self.set_status("● 正在获取示范片...", C_AMBER)
            self.log("\n[示范素材] 正在下载官方高清电影示范原片 (带台词对白)...")
            from download_video_resource import download_demo_movie
            demo_path = download_demo_movie(0)
            if demo_path and os.path.exists(demo_path):
                self.selected_video_path = demo_path
                name = os.path.basename(demo_path)
                self.root.after(0, lambda: self.selected_label.config(text=f"当前指定源: 【{name}】", fg=C_CYAN))
                self.log(f"\n[示范素材就绪] 电影示范长视频已下载完成: {name}\n")
            self.set_status("● IDLE (待命)", C_GREEN)

        threading.Thread(target=demo_worker, daemon=True).start()

    def _execute_streaming(self, cmd_or_bat, task_name=""):
        if isinstance(cmd_or_bat, list):
            cmd = cmd_or_bat
            is_shell = False
        else:
            bat_path = os.path.join(BASE_DIR, cmd_or_bat)
            if not os.path.exists(bat_path):
                self.log(f"[错误] 找不到批处理文件: {bat_path}")
                return False
            cmd = bat_path
            is_shell = True

        try:
            process = subprocess.Popen(
                cmd,
                cwd=BASE_DIR,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                shell=is_shell,
                text=True,
                encoding="gbk" if is_shell else "utf-8",
                errors="ignore"
            )
            for line in process.stdout:
                line_str = line.strip()
                if line_str:
                    self.log(line_str)
                    self._parse_live_line(line_str)
            process.wait()
            return process.returncode == 0
        except Exception as e:
            self.log(f"[异常] 执行出错: {e}")
            return False

    def run_slicing_task(self):
        if self.is_running:
            messagebox.showwarning("流水线正在运行", "当前已有任务正在执行中，请稍候...")
            return

        def worker():
            self.is_running = True
            self.set_status("● 正在执行 AI 切片...", C_RED)
            self.update_progress(0, "正在启动切片流水线...")
            self.log("\n========================================================")
            self.log("🎬 启动长视频智能切片流水线 (存入 G:\\矩阵短视频\\已完成切片\\日期)")
            self.log("========================================================")

            py_exe = sys.executable
            if os.path.exists(r"C:\Program Files\Python311\python.exe"):
                py_exe = r"C:\Program Files\Python311\python.exe"

            cmd = [py_exe, "-u", os.path.join(BASE_DIR, "long_to_shorts_pipeline.py")]
            if self.selected_video_path and os.path.exists(self.selected_video_path):
                cmd.extend(["--input", self.selected_video_path])
            if hasattr(self, "var_duration"):
                cmd.extend(["--duration", str(self.var_duration.get())])
            cmd.extend(["--max-clips", "1"])
            if not self.var_scenedetect.get():
                cmd.append("--no-scenedetect")
            if not self.var_mediapipe.get():
                cmd.append("--no-mediapipe")
            if not self.var_autoeditor.get():
                cmd.append("--no-autoeditor")

            self._execute_streaming(cmd, "智能切片")
            self._refresh_slice_path_monitor()
            self.is_running = False
            self.set_status("● IDLE (待命)", C_GREEN)

        threading.Thread(target=worker, daemon=True).start()

    def run_task(self, task_name, bat_filename):
        def worker():
            self.log(f"\n[开始] 正在执行任务: {task_name} ({bat_filename}) ...")
            self._execute_streaming(bat_filename, task_name)
            self.log(f"[完成] 任务 [{task_name}] 执行完毕！\n")

        threading.Thread(target=worker, daemon=True).start()

    def run_matrix_publish_now(self):
        """立即执行一次全矩阵分发 (小红书/抖音/YouTube/Instagram)"""
        if self.is_running:
            messagebox.showwarning("正在运行", "当前已有任务正在执行中，请稍候...")
            return

        def worker():
            self.is_running = True
            self.set_status("● 全球矩阵发布中...", C_AMBER)
            for k in self.platform_badges:
                self.update_platform_status(k, "【准备发布...】", C_AMBER)

            py_exe = sys.executable
            if os.path.exists(r"C:\Program Files\Python311\python.exe"):
                py_exe = r"C:\Program Files\Python311\python.exe"

            cmd = [py_exe, "-u", os.path.join(BASE_DIR, "publish_multi_platform.py"), "--count", "2"]
            self._execute_streaming(cmd, "全球矩阵发布")
            self._refresh_slice_path_monitor()
            self.is_running = False
            self.set_status("● IDLE (待命)", C_GREEN)

        threading.Thread(target=worker, daemon=True).start()

    def run_all_pipeline(self):
        def master_worker():
            self.log("\n" + "=" * 65)
            self.log("🚀 开始执行全自动流水线：抓取选题 ➔ 智能切片 ➔ 全球矩阵发布")
            self.log("=" * 65)
            
            # 第一步：抓取选题
            self.log("\n--- [步骤 1/3] 正在抓取热门爆款影视选题 ---")
            self._execute_streaming("4_抓取欧乐热门影视并生成选题.bat", "抓取选题")
            
            # 第二步：智能切片
            self.log("\n--- [步骤 2/3] 正在生成高光影视竖屏切片 (存入日期文件夹) ---")
            py_exe = sys.executable
            if os.path.exists(r"C:\Program Files\Python311\python.exe"):
                py_exe = r"C:\Program Files\Python311\python.exe"
            cmd = [py_exe, "-u", os.path.join(BASE_DIR, "long_to_shorts_pipeline.py")]
            if self.selected_video_path and os.path.exists(self.selected_video_path):
                cmd.extend(["--input", self.selected_video_path])
            if not self.var_scenedetect.get():
                cmd.append("--no-scenedetect")
            if not self.var_mediapipe.get():
                cmd.append("--no-mediapipe")
            if not self.var_autoeditor.get():
                cmd.append("--no-autoeditor")
            self._execute_streaming(cmd, "长视频切片")
            
            # 第三步：全球矩阵发布
            self.log("\n--- [步骤 3/3] 正在执行全球矩阵自动发布 (小红书/X/IG/YouTube) ---")
            cmd_pub = [py_exe, "-u", os.path.join(BASE_DIR, "publish_multi_platform.py"), "--count", "2"]
            self._execute_streaming(cmd_pub, "全球矩阵发布")
            self._refresh_slice_path_monitor()

            self.log("\n" + "=" * 65)
            self.log("🎉 全自动流水线执行完毕！成果视频已按日归档至 G:\\矩阵短视频\\已发布！")
            self.log("=" * 65 + "\n")

        threading.Thread(target=master_worker, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = MediaFactoryDashboard(root)
    root.mainloop()
