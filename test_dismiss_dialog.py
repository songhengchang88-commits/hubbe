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
    time.sleep(5)
    
    # Check dialog
    abandon_btn = page.locator('button:has-text("放弃"), div[role="button"]:has-text("放弃"), :has-text("放弃编辑")').last
    if abandon_btn.count() > 0 and abandon_btn.is_visible():
        print("Found abandon button, clicking it...")
        abandon_btn.click()
        time.sleep(3)
        print("Clicked abandon button!")
    else:
        print("No visible abandon button found directly.")
        
    # Check upload file input
    file_inputs = page.locator('input[type="file"]')
    print("File inputs after handling dialog:", file_inputs.count())
    
    ctx.close()
