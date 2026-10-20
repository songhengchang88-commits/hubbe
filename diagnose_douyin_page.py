import os, sys, time
from playwright.sync_api import sync_playwright

data_dir = r"C:\Users\Administrator\Desktop\自媒体全自动工厂\browser_data\douyin"
out_img = r"C:\Users\Administrator\Desktop\自媒体全自动工厂\browser_data\douyin_upload_screen.png"

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(user_data_dir=data_dir, channel="msedge", headless=True)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("https://creator.douyin.com/creator-micro/content/upload", wait_until="domcontentloaded", timeout=60000)
    print("Navigated, waiting 8 seconds for dynamic components...")
    time.sleep(8)
    print("Current URL:", page.url)
    
    # Save screenshot
    page.screenshot(path=out_img)
    print(f"Screenshot saved to: {out_img}")
    
    # Check frames
    print("Frames count:", len(page.frames))
    for i, f in enumerate(page.frames):
        print(f"  Frame {i}: url={f.url}, name={f.name}")
        file_inputs = f.eval_on_selector_all('input[type="file"]', 'els => els.length')
        print(f"    file inputs in frame {i}: {file_inputs}")
        
    # Check main page elements
    body_text = page.inner_text('body')
    print("Body text preview (first 300 chars):", repr(body_text[:300]))
    
    ctx.close()
