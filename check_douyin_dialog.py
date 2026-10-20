# -*- coding: utf-8 -*-
import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
import time
from playwright.sync_api import sync_playwright

data_dir = r"C:\Users\Administrator\Desktop\自媒体全自动工厂\browser_data\douyin"

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(user_data_dir=data_dir, channel="msedge", headless=True)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("https://creator.douyin.com/creator-micro/content/upload", wait_until="domcontentloaded", timeout=60000)
    time.sleep(6)
    
    # Check all modals/buttons
    btns = page.locator("button, div[role='button']").all_inner_texts()
    print("ALL BUTTONS:")
    for b in btns:
        if b.strip():
            print("  BTN:", b.strip().replace("\n", " "))
            
    # Check texts
    for t in ["放弃", "重新上传", "继续编辑", "未上传完", "确定", "取消", "知道了", "暂不"]:
        cnt = page.locator(f':has-text("{t}")').count()
        if cnt > 0:
            print(f"Found keyword '{t}': {cnt} elements")
            
    ctx.close()
