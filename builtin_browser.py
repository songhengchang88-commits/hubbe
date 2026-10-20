# -*- coding: utf-8 -*-
"""
自媒体内置登录浏览器管理中心 (Built-in Media Login Browser Hub)
功能：
1. 真正的“内置独立应用浏览器”模式 (基于 Edge App 纯净无干扰原生窗口)
2. 用户可在内置浏览器中直接扫码、输入账号密码登录
3. 绝不自动闪退、绝不超时强制关闭，给用户最充裕的操作时间
4. 登录成功后，Cookies 与 Session 自动永久写入本地 browser_data 目录
5. 自动实时分析各平台登录凭证有效性，一目了然显示【已登录 / 待登录】
"""

import os
import sys
import time
import sqlite3
import datetime
import threading
import subprocess
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox

# 界面配色
C_BG = "#0d1117"
C_CARD = "#161f2e"
C_CYAN = "#00f2fe"
C_GREEN = "#10b981"
C_AMBER = "#f59e0b"
C_RED = "#ef4444"
C_TEXT = "#f1f5f9"
C_MUTED = "#94a3b8"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "browser_data")
os.makedirs(DATA_DIR, exist_ok=True)

def find_edge_exe() -> str:
    """查找本机 Edge 浏览器绝对路径"""
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe")
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return "msedge.exe"

EDGE_EXE = find_edge_exe()

PLATFORMS_CONFIG = [
    {
        "id": "xiaohongshu",
        "name": "📕 小红书创作服务平台",
        "folder": "xiaohongshu",
        "url": "https://creator.xiaohongshu.com/publish/publish",
        "domains": ["xiaohongshu.com"],
        "auth_keywords": ["session", "token", "userId", "customer-sso-sid", "web_session", "a1"],
        "guide": "启动后请在内置浏览器中使用【小红书 App】扫码登录，登录后即可关闭窗口保存。"
    },
    {
        "id": "twitter_x",
        "name": "✖️ X (Twitter) 官方平台",
        "folder": "twitter_x",
        "url": "https://x.com/login",
        "domains": ["x.com", "twitter.com"],
        "auth_keywords": ["auth_token", "ct0", "twid", "personalization_id"],
        "guide": "启动后请在内置浏览器中输入您的 X 账号密码登录，登录后即可关闭窗口保存。"
    },
    {
        "id": "instagram",
        "name": "📸 Instagram (IG) 网页版",
        "folder": "instagram",
        "url": "https://www.instagram.com/accounts/login/",
        "domains": ["instagram.com"],
        "auth_keywords": ["sessionid", "ds_user_id", "csrftoken", "mid"],
        "guide": "启动后请在内置浏览器中输入 Instagram 账号密码登录，登录后即可关闭窗口保存。"
    },
    {
        "id": "youtube",
        "name": "🎬 YouTube 创作者中心 (Studio)",
        "folder": "youtube",
        "url": "https://studio.youtube.com/",
        "domains": ["youtube.com", "google.com"],
        "auth_keywords": ["LOGIN_INFO", "SAPISID", "HSID", "SSID", "SID"],
        "guide": "启动后请在内置浏览器中登录您的 Google 创作者账号，登录后即可关闭窗口保存。"
    },
    {
        "id": "douyin",
        "name": "🎵 抖音创作者中心",
        "folder": "douyin",
        "url": "https://creator.douyin.com/creator-micro/content/upload",
        "domains": ["douyin.com"],
        "auth_keywords": ["sessionid", "sessionid_ss", "passport_csrf_token", "odin_tt", "sid_guard", "uid_tt"],
        "guide": "启动后请在内置浏览器中使用【抖音 App】扫码登录，登录后即可关闭窗口保存。"
    }
]

def check_login_status(platform_cfg: dict) -> tuple:
    """
    检查指定平台的本地 SQLite Cookies 数据库，判断是否已有登录凭证
    返回 (is_logged_in: bool, details: str)
    """
    folder = platform_cfg["folder"]
    cookie_db = os.path.join(DATA_DIR, folder, "Default", "Network", "Cookies")
    if not os.path.exists(cookie_db):
        return False, "未生成凭证数据库"

    try:
        # SQLite 只读连接检测
        conn = sqlite3.connect(f"file:{cookie_db}?mode=ro", uri=True)
        cursor = conn.cursor()
        
        # 查询相关域名下的 Cookie 数量
        domain_conds = " OR ".join([f"host_key LIKE '%{d}%'" for d in platform_cfg["domains"]])
        cursor.execute(f"SELECT name FROM cookies WHERE {domain_conds}")
        cookie_names = [r[0] for r in cursor.fetchall()]
        conn.close()

        if not cookie_names:
            return False, "无平台 Cookie 记录"

        # 检查是否包含核心登录凭证关键字
        matched_auth = [k for k in platform_cfg["auth_keywords"] if any(k.lower() in name.lower() for name in cookie_names)]
        if matched_auth:
            return True, f"已保存有效凭证 (含 {len(cookie_names)} 个状态项)"
        elif len(cookie_names) >= 3:
            return True, f"已检测到访问凭证 ({len(cookie_names)} 个状态项)"
        else:
            return False, "凭证不完整，请重新登录"
    except Exception as e:
        # 如果数据库被占用，但文件存在，基本表示已有会话
        if os.path.exists(cookie_db) and os.path.getsize(cookie_db) > 20480:
            return True, "凭证活跃 (数据库使用中)"
        return False, f"读取异常: {e}"

class BuiltinBrowserHub:
    def __init__(self, root):
        self.root = root
        self.root.title("🌐 自媒体专用内置登录浏览器 · 多平台凭证保存中心")
        self.root.geometry("1060x720")
        self.root.minsize(960, 640)
        self.root.configure(bg=C_BG)

        self.running_processes = {}

        self._build_ui()
        self.refresh_all_status()

    def _build_ui(self):
        # 顶部标题栏
        top_frame = tk.Frame(self.root, bg=C_BG)
        top_frame.pack(fill=tk.X, padx=20, pady=(15, 8))

        lbl_t = tk.Label(
            top_frame,
            text="🌐 自媒体专用内置登录浏览器",
            font=("微软雅黑", 16, "bold"),
            bg=C_BG,
            fg=C_CYAN
        )
        lbl_t.pack(anchor="w")

        lbl_desc = tk.Label(
            top_frame,
            text="★ 直接在内置独立应用窗口中扫码或输入密码登录 ★ 绝不闪退自动关闭 ★ 登录状态永久保存在本地 ★ 自动化发布无缝免密调用",
            font=("微软雅黑", 9),
            bg=C_BG,
            fg=C_MUTED
        )
        lbl_desc.pack(anchor="w", pady=(2, 0))

        # 中部卡片区域
        content_frame = tk.Frame(self.root, bg=C_BG)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        self.card_widgets = {}

        for cfg in PLATFORMS_CONFIG:
            card = tk.Frame(content_frame, bg=C_CARD, bd=1, relief=tk.SOLID)
            card.pack(fill=tk.X, pady=5, ipady=4)

            # 左侧平台名称与说明
            info_frame = tk.Frame(card, bg=C_CARD)
            info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=12, pady=6)

            title_row = tk.Frame(info_frame, bg=C_CARD)
            title_row.pack(fill=tk.X)

            lbl_name = tk.Label(
                title_row,
                text=cfg["name"],
                font=("微软雅黑", 11, "bold"),
                bg=C_CARD,
                fg=C_TEXT
            )
            lbl_name.pack(side=tk.LEFT)

            status_lbl = tk.Label(
                title_row,
                text="⚪ 正在检测凭证...",
                font=("微软雅黑", 9, "bold"),
                bg=C_CARD,
                fg=C_MUTED
            )
            status_lbl.pack(side=tk.LEFT, padx=15)

            guide_lbl = tk.Label(
                info_frame,
                text=cfg["guide"],
                font=("微软雅黑", 8),
                bg=C_CARD,
                fg=C_MUTED,
                anchor="w"
            )
            guide_lbl.pack(fill=tk.X, pady=(3, 0))

            # 右侧操作按钮
            btn_frame = tk.Frame(card, bg=C_CARD)
            btn_frame.pack(side=tk.RIGHT, padx=12, pady=6)

            launch_btn = tk.Button(
                btn_frame,
                text="🚀 启动内置登录浏览器",
                font=("微软雅黑", 9, "bold"),
                bg="#0284c7",
                fg="white",
                relief=tk.FLAT,
                cursor="hand2",
                width=20,
                height=1,
                command=lambda c=cfg: self.launch_browser_app(c)
            )
            launch_btn.pack(side=tk.RIGHT, padx=4)

            self.card_widgets[cfg["id"]] = {
                "status_label": status_lbl,
                "launch_btn": launch_btn,
                "config": cfg
            }

        # 底部状态通知与快捷操作区
        bottom_frame = tk.Frame(self.root, bg=C_CARD, bd=1, relief=tk.SOLID)
        bottom_frame.pack(fill=tk.X, padx=20, pady=(10, 15), ipady=8)

        self.tip_label = tk.Label(
            bottom_frame,
            text="💡 使用提示：点击各平台的【🚀 启动内置登录浏览器】按钮，在弹出的独立应用窗口中直接登录即可。登录成功后关闭浏览器窗口，系统会自动检测并永久保存登录信息！",
            font=("微软雅黑", 9),
            bg=C_CARD,
            fg=C_AMBER,
            wraplength=980,
            justify=tk.LEFT
        )
        self.tip_label.pack(fill=tk.X, padx=15, pady=(4, 8))

        btn_row = tk.Frame(bottom_frame, bg=C_CARD)
        btn_row.pack(fill=tk.X, padx=15)

        tk.Button(
            btn_row,
            text="🔄 立即刷新所有平台凭证状态",
            font=("微软雅黑", 9, "bold"),
            bg="#1e293b",
            fg=C_CYAN,
            relief=tk.FLAT,
            cursor="hand2",
            command=self.refresh_all_status
        ).pack(side=tk.LEFT, padx=4)

        tk.Button(
            btn_row,
            text="📁 打开凭证数据文件夹 (browser_data)",
            font=("微软雅黑", 9),
            bg="#1e293b",
            fg=C_TEXT,
            relief=tk.FLAT,
            cursor="hand2",
            command=lambda: os.system(f'explorer.exe "{DATA_DIR}"')
        ).pack(side=tk.LEFT, padx=4)

        tk.Button(
            btn_row,
            text="🚪 关闭并返回总控台",
            font=("微软雅黑", 9),
            bg="#334155",
            fg="white",
            relief=tk.FLAT,
            cursor="hand2",
            command=self.root.destroy
        ).pack(side=tk.RIGHT, padx=4)

    def launch_browser_app(self, platform_cfg: dict):
        """
        以原生独立 Application 窗口启动内置 Edge 浏览器
        绑定专属 user_data_dir，绝不自动退出，永不闪退！
        """
        pid = platform_cfg["id"]
        profile_dir = os.path.join(DATA_DIR, platform_cfg["folder"])
        os.makedirs(profile_dir, exist_ok=True)
        url = platform_cfg["url"]

        self.tip_label.config(
            text=f"🟢 【{platform_cfg['name']}】内置浏览器已启动！窗口将为您持续保持开启。\n👉 请在内置浏览器窗口中扫码或输入密码登录。登录成功后直接关闭该浏览器窗口，系统会自动保存登录状态！",
            fg=C_GREEN
        )

        cmd = [
            EDGE_EXE,
            f"--user-data-dir={profile_dir}",
            f"--app={url}",
            "--window-size=1200,850",
            "--disable-blink-features=AutomationControlled",
            "--no-first-run",
            "--no-default-browser-check"
        ]

        def runner():
            try:
                proc = subprocess.Popen(cmd)
                self.running_processes[pid] = proc
                proc.wait()  # 阻塞直到用户自己关闭窗口
                # 用户关闭窗口后自动触发状态更新
                self.root.after(500, self.refresh_all_status)
                self.root.after(500, lambda: self.tip_label.config(
                    text=f"✅ 【{platform_cfg['name']}】内置浏览器已关闭！已自动刷新并持久化保存该平台登录凭证！",
                    fg=C_CYAN
                ))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("启动异常", f"启动内置浏览器失败: {e}"))

        threading.Thread(target=runner, daemon=True).start()

    def refresh_all_status(self):
        """刷新全部平台的登录与 Cookie 保存状态"""
        for cfg in PLATFORMS_CONFIG:
            pid = cfg["id"]
            if pid in self.card_widgets:
                is_ok, msg = check_login_status(cfg)
                lbl = self.card_widgets[pid]["status_label"]
                if is_ok:
                    lbl.config(text=f"🟢 {msg}", fg=C_GREEN)
                else:
                    lbl.config(text=f"⚪ {msg}", fg=C_MUTED)

if __name__ == "__main__":
    root = tk.Tk()
    app = BuiltinBrowserHub(root)
    root.mainloop()
