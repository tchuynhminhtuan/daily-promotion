import asyncio
import json
import os
from playwright.async_api import async_playwright

# --- 1. SETUP ---
# We define an async function because Playwright is asynchronous.
# This allows it to perform non-blocking operations (like waiting for a page to load).
async def run():
    print("🚀 Bắt đầu quá trình cào dữ liệu...")

    # 'async with' ensures resources are closed properly after use.
    async with async_playwright() as p:
        
        # --- 2. LAUNCH BROWSER ---
        # headless=False: Opens a visible browser window (Great for learning/debugging).
        # slow_mo=1000: Slows down operations by 1000ms so you can see what's happening.
        print("🌍 Đang mở trình duyệt Chromium...")
        browser = await p.chromium.launch(headless=False, slow_mo=1000)
        
        # Create a new browser context (like an Incognito window).
        # This isolates cookies and storage.
        context = await browser.new_context()
        
        # Open a new tab (Page).
        page = await context.new_page()

        # --- 3. NAVIGATION ---
        url = "https://support.apple.com/vi-vn/docs/iphone"
        print(f"🔗 Đang truy cập: {url}")
        await page.goto(url)

        # Wait for the page to be reasonably loaded.
        # 'domcontentloaded': HTML is parsed.
        # 'networkidle': Network connections have stopped (useful for heavy SPAs).
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except:
             print("⚠️ Hết thời gian chờ networkidle, tiếp tục chạy...")

        # --- 4. INTERACTION & EXTRACTION ---
        # Let's get the page title to verify.
        page_title = await page.title()
        print(f"📄 Tiêu đề trang: {page_title}")

        # Example: Scrape a list of manuals/links.
        # We look for anchor tags <a> that might be documentation links.
        # This selector looks for links inside a specific main content area (heuristic).
        # If we don't know the exact class, we can grabbing generic links for now.
        
        print("🔎 Đang tìm kiếm các liên kết tài liệu...")
        
        # 'locator' describes an element or list of elements.
        # Here find all 'a' tags that contain text 'iPhone' (just as an example).
        links = page.locator("a")
        count = await links.count()
        print(f"📊 Tìm thấy tổng cộng {count} thẻ <a> trên trang.")

        extracted_data = []

        # Loop through a subset to avoid spamming typical footer links
        # Better: use a CSS selector usually found in content lists
        # On Apple Support Docs, usually lists are in specific containers.
        # Let's try to infer relevant links by text length or content.
        
        for i in range(min(count, 50)): # Limit to first 50 for demo
            link = links.nth(i)
            # Only get text if the element is visible
            if await link.is_visible():
                text = await link.inner_text()
                href = await link.get_attribute("href")
                
                if text and href and len(text) > 5:
                    print(f"   - Found: {text.strip()} -> {href}")
                    extract_item = {
                        "text": text.strip(),
                        "url": href
                    }
                    extracted_data.append(extract_item)

        # --- 5. SCREENSHOT ---
        # Capture what the bot sees
        print("📸 Đang chụp ảnh màn hình...")
        os.makedirs("results", exist_ok=True)
        await page.screenshot(path="results/apple_docs_preview.png", full_page=True)

        # --- 6. SAVE DATA ---
        output_file = "results/apple_docs.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({
                "source": url,
                "title": page_title,
                "data": extracted_data
            }, f, ensure_ascii=False, indent=4)
            
        print(f"✅ Dữ liệu đã lưu vào: {output_file}")

        # Close the browser
        await browser.close()
        print("👋 Đã đóng trình duyệt.")

# Python Entry Point
if __name__ == "__main__":
    asyncio.run(run())
