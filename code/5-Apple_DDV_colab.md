# @title 1. Cài đặt môi trường (Chạy 1 lần đầu)
# @markdown Bấm nút **Play** (hình tam giác) bên trái để cài đặt.
# @markdown *Chờ khoảng 1-2 phút cho đến khi hiện thông báo "Cài đặt hoàn tất!".*

!pip install playwright
!playwright install chromium
!playwright install-deps
from IPython.display import clear_output
clear_output()
print("✅ Cài đặt hoàn tất! Bạn có thể chuyển sang Bước 2.")


# @title 2. Nhập link và Chạy Tool
# @markdown Dán danh sách link sản phẩm vào ô bên dưới (mỗi link cách nhau bằng dấu phẩy hoặc xuống dòng).
# @markdown **Nếu để trống, tool sẽ chạy danh sách mặc định (toàn bộ sản phẩm Apple).**

import asyncio
import csv
import os
import random
import re
from datetime import datetime
import pytz
from playwright.async_api import async_playwright

# --- Cấu hình Input ---
ds_link = "" #@param {type:"string"}

# --- Danh sách mặc định (từ sites.py) ---
default_ddv_urls = [
    'https://didongviet.vn/dien-thoai/iphone-13-128gb.html',
    'https://didongviet.vn/dien-thoai/iphone-14-128gb.html',
    # 'https://didongviet.vn/dien-thoai/iphone-15-128gb.html',
    # 'https://didongviet.vn/dien-thoai/iphone-15-256gb.html',
    # 'https://didongviet.vn/dien-thoai/iphone-16-128gb.html',
    # 'https://didongviet.vn/dien-thoai/iphone-16-plus-128gb.html',
    # 'https://didongviet.vn/dien-thoai/iphone-16-plus-256gb.html',
    # 'https://didongviet.vn/dien-thoai/iphone-16-pro-128gb.html',
    'https://didongviet.vn/dien-thoai/iphone-16-pro-max-256gb.html',
    # 'https://didongviet.vn/dien-thoai/iphone-16e.html',
    # 'https://didongviet.vn/dien-thoai/iphone-17-256gb.html',
    # 'https://didongviet.vn/dien-thoai/iphone-17-pro-1tb.html',
    # 'https://didongviet.vn/dien-thoai/iphone-17-pro-256gb.html',
    # 'https://didongviet.vn/dien-thoai/iphone-17-pro-512gb.html',
    # 'https://didongviet.vn/dien-thoai/iphone-17-pro-max-1tb.html',
    'https://didongviet.vn/dien-thoai/iphone-17-pro-max-256gb.html',
    # 'https://didongviet.vn/dien-thoai/iphone-air-1tb.html',
    # 'https://didongviet.vn/dien-thoai/iphone-air-256gb.html',
    # 'https://didongviet.vn/dien-thoai/iphone-air-512gb.html',
]

# Xử lý input
if ds_link.strip():
    raw_links = ds_link.replace(' ', ',').replace('\n', ',').split(',')
    urls_to_process = [link.strip() for link in raw_links if link.strip()]
    print(f"📋 Đang chạy danh sách tùy chỉnh ({len(urls_to_process)} link).")
else:
    urls_to_process = list(default_ddv_urls)
    print(f"📋 Đang chạy danh sách mặc định ({len(urls_to_process)} link).")


# --- Configuration ---
MAX_CONCURRENT_TABS = 4 # Optimized for Colab
HEADLESS = True
USER_AGENT_LIST = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

# --- Helper Functions ---
async def get_text_safe(page, selector, timeout=2000):
    try:
        loc = page.locator(selector).first
        if await loc.count() > 0 and await loc.is_visible(timeout=timeout):
            return await loc.inner_text()
    except: pass
    return ""

async def wait_for_overlay(page):
    try:
        # Generic overlay closer
        close_btns = page.locator("button[aria-label='Close'], .close-popup, .popup-close")
        if await close_btns.count() > 0 and await close_btns.first.is_visible():
            await close_btns.first.click()
    except: pass

async def add_stealth_scripts(page):
    await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        window.chrome = { runtime: {} };
        Object.defineProperty(navigator, 'languages', { get: () => ['vi-VN', 'vi', 'en-US', 'en'] });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
        Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ? Promise.resolve({ state: 'granted' }) : originalQuery(parameters)
        );
    """)

# --- File Handling ---
def get_current_date():
    tz = pytz.timezone('Asia/Ho_Chi_Minh')
    return datetime.now(tz).strftime("%Y-%m-%d")

def setup_csv(date_str):
    file_path = f"5-ddv-{date_str}.csv"
    img_dir = 'img_ddv'
    if not os.path.exists(img_dir):
        os.makedirs(img_dir)
        
    # Overwrite if exists
    with open(file_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=[
            "Product_Name", "Color", "Ton_Kho", "Store_Count", "Gia_Niem_Yet", "Gia_Khuyen_Mai",
             "Date", "Khuyen_Mai", "Thanh_Toan", "Other_promotion", "Link", "screenshot_name"
        ], delimiter=";")
        writer.writeheader()
    return file_path

async def write_to_csv(file_path, data, lock):
    async with lock:
        with open(file_path, "a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=[
                "Product_Name", "Color", "Ton_Kho", "Store_Count", "Gia_Niem_Yet", "Gia_Khuyen_Mai",
                 "Date", "Khuyen_Mai", "Thanh_Toan", "Other_promotion", "Link", "screenshot_name"
            ], delimiter=";")
            writer.writerow(data)

# --- Core Scrapers ---
async def scrape_product(page, url, csv_path, csv_lock, forced_color="Unknown", screenshot=False):
    local_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    date_str = datetime.now(local_tz).strftime('%Y-%m-%d')

    # 1. Product Name
    product_name = await get_text_safe(page, "h1")
    if not product_name: product_name = "Unknown"
    
    # 2. Price
    gia_khuyen_mai = 0
    gia_niem_yet = 0
    
    try:
        gkm_str = await get_text_safe(page, "//div[@class='flex flex-row items-end gap-4']/div")
        if gkm_str:
            gia_khuyen_mai = int(re.sub(r'[^\d]', '', gkm_str)) if re.search(r'\d', gkm_str) else 0

        gny_str = await get_text_safe(page, "//div[@class='flex flex-row items-end gap-4']/span/p[contains(@class, 'line-through')]")
        if gny_str:
            gia_niem_yet = int(re.sub(r'[^\d]', '', gny_str)) if re.search(r'\d', gny_str) else 0
            
        # Fallback
        if gia_khuyen_mai == 0:
             btn_gkm = await get_text_safe(page, "//button[contains(@class, 'bg-white shadow shadow-red-500/50')]/p")
             if btn_gkm:
                 gia_khuyen_mai = int(re.sub(r'[^\d]', '', btn_gkm)) if re.search(r'\d', btn_gkm) else 0
             if gia_niem_yet == 0:
                 btn_gny = await get_text_safe(page, "//button[contains(@class, 'bg-white shadow shadow-red-500/50')]//div/p")
                 if btn_gny:
                      gia_niem_yet = int(re.sub(r'[^\d]', '', btn_gny)) if re.search(r'\d', btn_gny) else 0

        if gia_niem_yet == 0 and gia_khuyen_mai > 0:
            gia_niem_yet = gia_khuyen_mai
    except: pass

    # 3. Stock
    ton_kho = "No" 
    try:
        buy_text_loc = page.locator("//button//p").filter(has_text=re.compile("mua ngay", re.IGNORECASE)).first
        if await buy_text_loc.count() > 0 and await buy_text_loc.is_visible():
             ton_kho = "Yes"
    except: pass

    # Store Count
    Store_Count = "0"
    try:
        sc_loc = page.locator("//div[@class='py-2']/p/span").first
        if await sc_loc.count() > 0:
             Store_Count = await sc_loc.inner_text()
    except: pass

    # 4. Promos
    khuyen_mai = ""
    thanh_toan = ""
    try:
        # Expand dropdowns
        dropdowns = page.locator("//div[@class='w-full my-2']")
        cnt_dd = await dropdowns.count()
        if cnt_dd > 0:
            for i in range(cnt_dd):
                try: 
                    if await dropdowns.nth(i).is_visible():
                        await dropdowns.nth(i).click(force=True)
                        await page.wait_for_timeout(100)
                except: pass

        km_loc = page.locator("//div[@class='border rounded-lg overflow-hidden w-full']")
        if await km_loc.count() > 0:
            khuyen_mai = await km_loc.first.inner_text() 
            khuyen_mai = khuyen_mai.strip()

        tt_loc = page.locator("//div[@class='flex w-full flex-col items-start justify-start bg-white p-2']")
        if await tt_loc.count() > 0:
            thanh_toan = await tt_loc.first.inner_text()
            thanh_toan = thanh_toan.strip()
    except: pass

    # Screenshot
    screenshot_name = ""
    if screenshot:
        try:
            img_dir = 'img_ddv'
            safe_name = re.sub(r'[^\w\-\.]', '_', product_name)[:30]
            fname = f"{safe_name}_{forced_color}_{datetime.now().strftime('%H%M%S')}.png"
            await page.screenshot(path=os.path.join(img_dir, fname), full_page=True)
            screenshot_name = fname
        except: pass

    # Save
    data = {
        "Product_Name": product_name,
        "Color": forced_color,
        "Ton_Kho": ton_kho,
        "Store_Count": Store_Count,
        "Gia_Niem_Yet": gia_niem_yet,
        "Gia_Khuyen_Mai": gia_khuyen_mai,
        "Date": date_str,
        "Khuyen_Mai": khuyen_mai,
        "Thanh_Toan": thanh_toan,
        "Other_promotion": "",
        "Link": url,
        "screenshot_name": screenshot_name
    }
    await write_to_csv(csv_path, data, csv_lock)
    print(f"Saved: {product_name} | {forced_color} | {gia_khuyen_mai}")

async def process_url(semaphore, browser, url, csv_path, csv_lock):
    async with semaphore:
        page = await browser.new_page(
            user_agent=random.choice(USER_AGENT_LIST),
            viewport={"width": 1920, "height": 1080},
            locale="vi-VN",
            timezone_id="Asia/Ho_Chi_Minh"
        )
        await add_stealth_scripts(page)
        
        print(f"Processing: {url}")
        try:
            try:
                await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            except:
                 print(f"Retry loading {url}...")
                 await page.goto(url, timeout=60000, wait_until="domcontentloaded")

            await wait_for_overlay(page)
            
            # --- COLOR STRATEGY: Find, Deduplicate, Click, Scrape ---
            # Strict Selector (excludes storage/buy buttons)
            col_selector = "//div[contains(@class, 'cursor-pointer')][contains(@class, 'rounded')][not(ancestor::a[@href])][not(ancestor::button)]"
            
            candidates = page.locator(col_selector)
            count = await candidates.count()
            
            color_names = []
            for i in range(count):
                btn = candidates.nth(i)
                if await btn.is_visible():
                    txt = await btn.inner_text()
                    txt = txt.strip()
                    # Filter invalid text
                    if not txt or "GB" in txt or "TB" in txt or "MUA" in txt.upper(): continue
                    # Filter disabled
                    class_attr = await btn.get_attribute("class")
                    if class_attr and ("opacity-40" in class_attr or "pointer-events-none" in class_attr or "bg-gray-200" in class_attr):
                        continue
                    color_names.append(txt)

            # Deduplicate
            unique_colors = sorted(list(set(color_names)), key=color_names.index) if color_names else []

            if not unique_colors:
                 # No colors? Scrape default view
                 await scrape_product(page, url, csv_path, csv_lock, forced_color="Default", screenshot=True)
            else:
                 # Click each Unique Color
                 for col_name in unique_colors:
                    try:
                        # RE-QUERY by text to avoid Stale Elements
                        fresh_btn = page.locator(col_selector).filter(has_text=col_name).first
                        
                        if await fresh_btn.count() > 0 and await fresh_btn.is_visible():
                             await fresh_btn.click(force=True)
                             await page.wait_for_timeout(2000) # DOM refresh wait
                             await scrape_product(page, url, csv_path, csv_lock, forced_color=col_name, screenshot=True)
                        else:
                            print(f"  Color not found/visible: {col_name}")
                    except Exception as e:
                        print(f"Error clicking color {col_name}: {e}")

        except Exception as e:
            print(f"Error processing URL {url}: {e}")
        finally:
            await page.close()

async def main():
    date_str = get_current_date()
    csv_path = setup_csv(date_str)
    csv_lock = asyncio.Lock()
    
    global urls_to_process
    print(f"Found {len(urls_to_process)} URLs to process.")
    
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TABS)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=HEADLESS,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-setuid-sandbox"]
        )
        
        tasks = [process_url(semaphore, browser, url, csv_path, csv_lock) for url in urls_to_process]
        await asyncio.gather(*tasks)
            
        await browser.close()
    
    print("\n" + "="*50)
    print("🎉 HOÀN THÀNH! 🎉")
    print(f"📂 File kết quả: {csv_path}")
    print(f"🖼️ Thư mục ảnh: img_ddv")
    print("-" * 30)
    print("👇 HƯỚNG DẪN TẢI FILE:")
    print("1. Nhìn sang thanh bên trái, bấm vào biểu tượng Thư mục (📁).")
    print("2. Tìm file .csv và thư mục img_ddv.")
    print("3. Chuột phải > Download (Tải xuống).")
    print("="*50)

if __name__ == "__main__":
    await main()
