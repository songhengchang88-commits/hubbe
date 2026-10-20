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
    
    els = page.locator(':has-text("未上传完")')
    print("未上传完 count:", els.count())
    for i in range(min(5, els.count())):
        el = els.nth(i)
        print(f"  [{i}] tag={el.evaluate('e => e.tagName')}, class={el.evaluate('e => e.className')}, text={repr(el.inner_text()[:100])}")
        
    ctx.close()
