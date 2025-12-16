# @title 1. Cài đặt môi trường (Chạy 1 lần đầu)
# @markdown Bấm nút **Play** (hình tam giác) bên trái để cài đặt.
# @markdown *Chờ khoảng 1-2 phút cho đến khi hiện thông báo "Cài đặt hoàn tất!".*

!pip install playwright nest_asyncio
!playwright install chromium
!playwright install-deps
from IPython.display import clear_output
clear_output()
print("✅ Cài đặt hoàn tất! Bạn có thể chuyển sang Bước 2.")


# @title 2. Chạy Tool DDV
# @markdown Bấm nút **Play** (hình tam giác) để bắt đầu crawl data.
# @markdown *Kết quả sẽ được lưu vào file .csv và ảnh trong thư mục img_ddv.*

import asyncio
import csv
import os
import random
import re
from datetime import datetime
import pytz
import sys
import nest_asyncio
from playwright.async_api import async_playwright

# Apply nest_asyncio for Colab compatibility
nest_asyncio.apply()

# Configuration
# Output will be saved in /content/
OUTPUT_DIR = "/content" 
ENABLE_DEDUPLICATION = True 

# Stealth / Anti-bot constants
MAX_CONCURRENT_TABS = 5 # Reduced for Colab to prevent OOM
HEADLESS = True 

USER_AGENT_LIST = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

# URLs Inlined for Colab
DDV_URLS = [
    'https://didongviet.vn/dien-thoai/iphone-13-128gb.html',
    'https://didongviet.vn/dien-thoai/iphone-14-128gb.html',
    'https://didongviet.vn/dien-thoai/iphone-15-128gb.html',
    'https://didongviet.vn/dien-thoai/iphone-16-128gb.html',
    'https://didongviet.vn/dien-thoai/iphone-16-plus-128gb.html',
    'https://didongviet.vn/dien-thoai/iphone-16-pro-128gb.html',
    'https://didongviet.vn/dien-thoai/iphone-16-pro-max-256gb.html',
    'https://didongviet.vn/dien-thoai/iphone-16e.html',
    'https://didongviet.vn/dien-thoai/iphone-17-256gb.html',
    'https://didongviet.vn/dien-thoai/iphone-17-pro-256gb.html',
    'https://didongviet.vn/dien-thoai/iphone-17-pro-max-256gb.html',
    'https://didongviet.vn/dien-thoai/iphone-air-256gb.html',
    'https://didongviet.vn/may-tinh-bang/ipad-a16-11-inch-2025-128gb-wifi-5g.html',
    'https://didongviet.vn/may-tinh-bang/ipad-a16-11-inch-2025-128gb-wifi.html',
    'https://didongviet.vn/may-tinh-bang/ipad-air-m3-11-inch-128gb-wifi.html',
    'https://didongviet.vn/may-tinh-bang/ipad-pro-m5-11-inch-256gb-wifi.html',
    'https://didongviet.vn/apple-macbook-imac/mac-mini-m4-10core-cpu-10core-gpu-16gb-256gb.html',
    'https://didongviet.vn/apple-macbook-imac/mac-mini-m4-10core-cpu-10core-gpu-16gb-512gb.html',
    'https://didongviet.vn/apple-macbook-imac/macbook-air-m2-2024-13-inch-16gb-256gb.html',
    'https://didongviet.vn/apple-macbook-imac/macbook-air-m4-13-inch-16gb-256gb.html',
    'https://didongviet.vn/apple-macbook-imac/macbook-air-m4-13-inch-16gb-512gb.html',
    'https://didongviet.vn/apple-macbook-imac/macbook-air-m4-13-inch-24gb-512gb.html',
    'https://didongviet.vn/apple-macbook-imac/macbook-pro-2025-14-inch-m5-10core-cpu-10core-gpu-16gb-512gb.html',
    'https://didongviet.vn/apple-macbook-imac/macbook-pro-m3-pro-16-inch-2023-512gb.html',
    'https://didongviet.vn/dong-ho-thong-minh/apple-watch-se-2-2024-gps-40mm-vien-nhom-day-cao-su-s-m.html',
    'https://didongviet.vn/dong-ho-thong-minh/apple-watch-se-2-2024-gps-44mm-vien-nhom-day-cao-su-s-m.html',
    'https://didongviet.vn/dong-ho-thong-minh/apple-watch-se-2-2024-lte-40mm-vien-nhom-day-cao-su-s-m.html',
    'https://didongviet.vn/dong-ho-thong-minh/apple-watch-se-2-2024-lte-44mm-vien-nhom-day-cao-su-s-m.html',
    'https://didongviet.vn/dong-ho-thong-minh/apple-watch-se-3-2025-44mm-5g-vien-nhom-day-cao-su-s-m.html',
    'https://didongviet.vn/dong-ho-thong-minh/apple-watch-se-3-2025-44mm-gps-vien-nhom-day-cao-su-s-m.html',
    'https://didongviet.vn/dong-ho-thong-minh/apple-watch-se-3-2025-gps-40mm-vien-nhom-day-cao-su.html',
    'https://didongviet.vn/dong-ho-thong-minh/apple-watch-series-11-46mm-gps-vien-nhom-day-cao-su-m-l.html',
    'https://didongviet.vn/dong-ho-thong-minh/apple-watch-series-11-46mm-gps-vien-nhom-day-cao-su-s-m.html',
    'https://didongviet.vn/dong-ho-thong-minh/apple-watch-series-11-gps-42mm-nhom-day-cao-su-s-m.html',
    'https://didongviet.vn/dong-ho-thong-minh/apple-watch-series-9-45mm-gps-vien-nhom-day-cao-su-size-m-l.html',
    'https://didongviet.vn/thiet-bi-am-thanh/tai-nghe-apple-airpods-4.html',
    'https://didongviet.vn/thiet-bi-am-thanh/tai-nghe-apple-airpods-4-chong-on-chu-dong.html',
    'https://didongviet.vn/thiet-bi-am-thanh/airpods-pro-2-2023-usb-c.html',
    'https://didongviet.vn/thiet-bi-am-thanh/airpods-pro-2-2024.html',
    'https://didongviet.vn/thiet-bi-am-thanh/airpods-pro-3.html',
]

def setup_csv(base_path, date_str):
    output_dir = os.path.join(base_path, date_str)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    file_path = os.path.join(output_dir, f"5-ddv-{date_str}.csv")
    img_dir = os.path.join(output_dir, 'img_ddv')
    if not os.path.exists(img_dir):
        os.makedirs(img_dir)

    # Overwrite if exists, simple for Colab
    with open(file_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=[
            "Product_Name", "Color", "Ton_Kho", "Store_Count", "Gia_Niem_Yet", "Gia_Khuyen_Mai",
             "Date", "Khuyen_Mai", "Thanh_Toan", "Other_promotion", "Link", "screenshot_name"
        ], delimiter=";")
        writer.writeheader()
    print(f"CSV initialized at: {file_path}")
    return file_path

async def write_to_csv(file_path, data, lock):
    async with lock:
        with open(file_path, "a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=[
                "Product_Name", "Color", "Ton_Kho", "Store_Count", "Gia_Niem_Yet", "Gia_Khuyen_Mai",
                 "Date", "Khuyen_Mai", "Thanh_Toan", "Other_promotion", "Link", "screenshot_name"
            ], delimiter=";")
            writer.writerow(data)

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

async def add_stealth(page):
    await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

async def scrape_product(page, url, csv_path, csv_lock, forced_color="Unknown", screenshot=False):
    local_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    date_str = datetime.now(local_tz).strftime('%Y-%m-%d')

    # 1. Product Name
    product_name = await get_text_safe(page, "h1")
    if not product_name: product_name = "Unknown"
    
    # 2. Price (User Selectors)
    gia_khuyen_mai = 0
    gia_niem_yet = 0
    
    try:
        # Promo Price: //div[@class='flex flex-row items-end gap-4']/div
        gkm_str = await get_text_safe(page, "//div[@class='flex flex-row items-end gap-4']/div")
        if gkm_str:
            gia_khuyen_mai = int(re.sub(r'[^\d]', '', gkm_str)) if re.search(r'\d', gkm_str) else 0

        # Listed Price: //div[@class='flex flex-row items-end gap-4']/span/p[@class=' line-through']
        gny_str = await get_text_safe(page, "//div[@class='flex flex-row items-end gap-4']/span/p[contains(@class, 'line-through')]")
        if gny_str:
            gia_niem_yet = int(re.sub(r'[^\d]', '', gny_str)) if re.search(r'\d', gny_str) else 0
            
        if gia_niem_yet == 0 and gia_khuyen_mai > 0:
            gia_niem_yet = gia_khuyen_mai
            
    except Exception as e:
        print(f"Price Error: {e}")

    # 3. Stock
    ton_kho = "Yes"
    if await page.locator("text=Hết hàng").count() > 0 or await page.locator("text=Tạm hết hàng").count() > 0:
        ton_kho = "No"

    # User Request: Check for MUA NGAY in specific element to confirm stock
    try:
        buy_btn_text = await get_text_safe(page, "//p[@class='text-center text-15 font-bold text-white']")
        if "mua ngay" in buy_btn_text.lower():
             ton_kho = "Yes"
    except:
        pass

    # Stock Count (Users request: //div[@class='py-2']/p/span)
    stock_count = "0"
    try:
        sc_loc = page.locator("//div[@class='py-2']/p/span").first
        if await sc_loc.count() > 0:
             stock_count = await sc_loc.inner_text()
    except: pass

    # 4. Promos - Dropdowns & Extraction
    khuyen_mai = ""
    thanh_toan = ""
    
    try:
        # Click dropdowns to expand: //div[@class='w-full my-2']
        dropdowns = page.locator("//div[@class='w-full my-2']")
        cnt_dd = await dropdowns.count()
        if cnt_dd > 0:
            for i in range(cnt_dd):
                try:
                    if await dropdowns.nth(i).is_visible():
                        await dropdowns.nth(i).click(force=True)
                        await page.wait_for_timeout(200)
                except: pass

        # Extract Khuyen Mai: //div[@class='border rounded-lg overflow-hidden w-full']
        km_loc = page.locator("//div[@class='border rounded-lg overflow-hidden w-full']")
        if await km_loc.count() > 0:
            khuyen_mai = await km_loc.first.inner_text() 
            khuyen_mai = khuyen_mai.strip()

        # Extract Thanh Toan: //div[@class='flex w-full flex-col items-start justify-start bg-white p-2']
        tt_loc = page.locator("//div[@class='flex w-full flex-col items-start justify-start bg-white p-2']")
        if await tt_loc.count() > 0:
            thanh_toan = await tt_loc.first.inner_text()
            thanh_toan = thanh_toan.strip()

    except Exception as e: 
        print(f"Promo Error: {e}")
        pass

    # Screenshot
    screenshot_name = ""
    if screenshot:
        try:
            img_dir = os.path.join(os.path.dirname(csv_path), 'img_ddv')
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
        "Store_Count": stock_count,
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

async def process_url(page, url, csv_path, csv_lock, processed_urls, url_lock):
    print(f"Processing: {url}")
    try:
        await page.goto(url, timeout=60000, wait_until="domcontentloaded")
        await wait_for_overlay(page)
        
        # 1. Identify Storage options
        storages_found = []
        for st_txt in ["128GB", "256GB", "512GB", "1TB", "2TB"]:
            # Find element containing this text that looks like a button
            btn = page.locator(f"//div[contains(@class, 'cursor-pointer') or contains(@class, 'item-center')]").filter(has_text=st_txt).first
            if await btn.count() > 0:
                storages_found.append((st_txt, btn))
        
        if not storages_found:
             await process_colors(page, url, csv_path, csv_lock)
        else:
            # Iterate storage
            for st_name, st_btn in storages_found:
                try:
                    try:
                        href = await st_btn.evaluate("el => el.closest('a') ? el.closest('a').href : ''")
                        if href:
                             skip = False
                             if ENABLE_DEDUPLICATION:
                                 async with url_lock:
                                     processed_urls.add(href)
                    except: pass

                    # Click storage
                    if await st_btn.is_visible():
                        await st_btn.click(force=True)
                        await page.wait_for_timeout(300) 
                        await process_colors(page, url, csv_path, csv_lock)
                except Exception as e:
                    print(f"Error selecting storage {st_name}: {e}")

    except Exception as e:
        print(f"Error processing URL {url}: {e}")

async def process_colors(page, url, csv_path, csv_lock):
    candidates = page.locator("//div[contains(@class, 'cursor-pointer')][contains(@class, 'rounded')]")
    count = await candidates.count()
    
    color_buttons = []
    
    for i in range(count):
        btn = candidates.nth(i)
        txt = await btn.inner_text()
        
        if "GB" in txt or "TB" in txt: continue
        
        upper_txt = txt.upper()
        if "MUA" in upper_txt or "TRẢ GÓP" in upper_txt or "THÊM VÀO" in upper_txt: continue
        if not txt.strip(): continue
        
        color_buttons.append((txt.strip(), btn))

    unique_colors = []
    seen = set()
    for txt, btn in color_buttons:
        if txt not in seen:
            unique_colors.append((txt, btn))
            seen.add(txt)

    if not unique_colors:
        await scrape_product(page, url, csv_path, csv_lock, forced_color="Default", screenshot=True)
    else:
        for col_name, btn in unique_colors:
            try:
                await btn.click(force=True)
                await page.wait_for_timeout(300) 
                await scrape_product(page, url, csv_path, csv_lock, forced_color=col_name, screenshot=True)
            except Exception as e:
                print(f"Error scraping color {col_name}: {e}")

async def main():
    # Setup Paths for Colab
    base_path = OUTPUT_DIR
    
    local_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    date_str = datetime.now(local_tz).strftime('%Y-%m-%d')
    csv_path = setup_csv(base_path, date_str)
    csv_lock = asyncio.Lock()
    
    print(f"Starting Scraper. Saving to {csv_path}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS)
        context = await browser.new_context(
            user_agent=random.choice(USER_AGENT_LIST),
            viewport={"width": 1920, "height": 1080},
            extra_http_headers={
                "Upgrade-Insecure-Requests": "1",
                "Accept-Language": "vi-VN,vi;q=0.9",
            }
        )
        
        print(f"Processing {len(DDV_URLS)} URL(s).")
        
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_TABS)
        processed_urls = set()
        url_lock = asyncio.Lock()

        async def process_with_sem(url):
             async with semaphore:
                 if ENABLE_DEDUPLICATION:
                     async with url_lock:
                         if url in processed_urls:
                             return
                         processed_urls.add(url)

                 try:
                    page = await context.new_page()
                    await add_stealth(page) 
                    await process_url(page, url, csv_path, csv_lock, processed_urls, url_lock)
                    await page.close()
                 except Exception as e:
                     print(f"Task Error {url}: {e}")

        tasks = [process_with_sem(url) for url in DDV_URLS]
        await asyncio.gather(*tasks)
            
        await browser.close()
        
    print(f"\nCOMPLETED.")
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

# For Colab: Run directly with await
if 'ipykernel' in sys.modules:
    await main()
else:
    asyncio.run(main())
