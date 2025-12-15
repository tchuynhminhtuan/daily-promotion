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
import json
import re
import os
import sys
from datetime import datetime
import pytz
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# --- Cấu hình Input ---
ds_link = "" #@param {type:"string"}

# --- Danh sách mặc định (từ sites.py) ---
default_cps_urls = [
    'https://cellphones.com.vn/ipad-a16-11-inch.html',
    'https://cellphones.com.vn/apple-ipad-air-m3.html',
    'https://cellphones.com.vn/ipad-mini-7.html',
    'https://cellphones.com.vn/ipad-air-m3-11-inch-256gb.html',
    'https://cellphones.com.vn/ipad-a16-11-inch-5g.html',

    'https://cellphones.com.vn/macbook-air-m2-2022-16gb.html',
    'https://cellphones.com.vn/apple-macbook-air-13-m4-10cpu-8gpu-16gb-256gb-2025.html',
    'https://cellphones.com.vn/apple-macbook-air-13-m4-10cpu-10gpu-16gb-512gb-2025.html',
    'https://cellphones.com.vn/apple-macbook-air-13-m4-10cpu-10gpu-16gb-512gb-2025-sac-70w.html',

    'https://cellphones.com.vn/apple-watch-series-11-46mm.html',
    'https://cellphones.com.vn/apple-watch-series-11-42mm.html',
    'https://cellphones.com.vn/apple-watch-series-10-42mm.html',
    'https://cellphones.com.vn/apple-watch-series-10-42mm-vien-nhom-day-vai.html',
    'https://cellphones.com.vn/apple-watch-ultra-3-49mm-5g.html',
    'https://cellphones.com.vn/apple-watch-se-3-40mm.html',
    'https://cellphones.com.vn/apple-watch-se-3-44mm.html',

    'https://cellphones.com.vn/apple-airpods-4.html',
    'https://cellphones.com.vn/apple-airpods-pro-3.html',
    'https://cellphones.com.vn/apple-airpods-4-chong-on-chu-dong.html',
    'https://cellphones.com.vn/apple-airpods-pro-2-usb-c.html',
]

# Xử lý input
if ds_link.strip():
    raw_links = ds_link.replace(' ', ',').replace('\n', ',').split(',')
    urls_to_process = [link.strip() for link in raw_links if link.strip()]
    print(f"📋 Đang chạy danh sách tùy chỉnh ({len(urls_to_process)} link).")
else:
    urls_to_process = list(default_cps_urls)
    print(f"📋 Đang chạy danh sách mặc định ({len(urls_to_process)} link).")


# --- Configuration ---
MAX_CONCURRENT_TABS = 1 # CellphoneS might be sensitive to concurrency
HEADLESS = True
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

# --- Selectors ---
PRODUCT_NAME_SELECTOR = "h1"
PRICE_MAIN_SELECTOR = "//div[contains(@class, 'is-flex') and contains(@class, 'is-align-items-center')]/div[contains(@class, 'sale-price')]"
PRICE_SUB_SELECTOR = "//div[contains(@class, 'is-flex') and contains(@class, 'is-align-items-center')]/del[contains(@class, 'base-price')]"
PROMO_SELECTOR = "//div[contains(@class, 'box-product-promotion')]"
PAYMENT_PROMO_SELECTOR = "//div[contains(@class, 'box-more-promotion') and contains(@class, 'my-3')]"
COLOR_OPTIONS_SELECTOR = "//ul[contains(@class, 'list-variants')]/li"
BUY_BUTTON_SELECTOR = "//button[contains(@class, 'btn-cta') and contains(@class, 'order-button') and contains(@class, 'button--large')]"
VOUCHER_IMAGE_SELECTOR = "img[alt='voucher']"

# --- Helper Functions ---
async def get_text_safe(page, selector, timeout=2000):
    try:
        if await page.locator(selector).count() > 0:
            if await page.locator(selector).first.is_visible(timeout=timeout):
                return await page.locator(selector).first.inner_text()
        return ""
    except Exception:
        return ""

def get_current_date():
    tz = pytz.timezone('Asia/Ho_Chi_Minh')
    return datetime.now(tz).strftime("%Y-%m-%d")

def setup_csv(date_str):
    # Output directly to current directory in Colab
    file_path = f"6-cps-{date_str}.csv"
    
    # Create file with header if it doesn't exist
    if not os.path.exists(file_path) or os.stat(file_path).st_size == 0:
        with open(file_path, "w", newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=[
                "Product_Name", "Color", "Ton_Kho", "Gia_Niem_Yet", "Gia_Khuyen_Mai",
                 "Date", "Khuyen_Mai", "Thanh_Toan", "Link", "Voucher_Image", "screenshot_name"
            ], delimiter=";")
            writer.writeheader()
    return file_path

def write_to_csv(file_path, data):
    with open(file_path, "a", newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=[
            "Product_Name", "Color", "Ton_Kho", "Gia_Niem_Yet", "Gia_Khuyen_Mai",
             "Date", "Khuyen_Mai", "Thanh_Toan", "Link", "Voucher_Image", "screenshot_name"
        ], delimiter=";")
        writer.writerow(data)

# --- Main Logic ---
async def process_url(semaphore, browser, url, csv_path):
    async with semaphore:
        page = await browser.new_page(
            user_agent=USER_AGENT,
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1,
        )
        
        # Anti-detection script
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        try:
            print(f"Processing: {url}")
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_timeout(5000) # Wait for dynamic content

            # Color Iteration
            color_btns = page.locator(COLOR_OPTIONS_SELECTOR)
            count = await color_btns.count()
            
            if count > 0:
                print(f"Found {count} color options.")
                for i in range(count):
                    # Re-locate to avoid stale elements
                    color_btns = page.locator(COLOR_OPTIONS_SELECTOR)
                    btn = color_btns.nth(i)
                    
                    if await btn.is_visible():
                        # Try to get color name
                        # Structure: li > div > span > strong OR just text in div
                        color_name = await btn.inner_text()
                        color_name = color_name.split('\n')[0].strip() # Take first line usually name
                        
                        print(f"Clicking Color [{i}]: {color_name}", flush=True)
                        
                        # Click logic
                        await btn.click(force=True)
                        await page.wait_for_timeout(2000) # Wait for update
                        
                        await scrape_product_data(page, url, csv_path, color_name)
            else:
                print("No color options found. Scraping current page.")
                await scrape_product_data(page, url, csv_path, "Unknown")

        except Exception as e:
            print(f"Error processing {url}: {e}")
        finally:
            await page.close()

async def scrape_product_data(page, url, csv_path, color_name):
    # Time setup
    local_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    now_utc = datetime.now(pytz.utc)
    date_str = now_utc.astimezone(local_tz).strftime('%Y-%m-%d')

    # Product Name
    product_name = await get_text_safe(page, PRODUCT_NAME_SELECTOR)
    if not product_name:
         product_name = await page.title()
    
    # Clean Name
    to_remove = ["Chính hãng", " I ", " | ", " VN/A", " Apple Việt Nam", "Chính Hãng"]
    for item in to_remove:
        product_name = product_name.replace(item, "")
    product_name = product_name.strip()

    # Stock (Ton_Kho)
    ton_kho = "No"
    try:
        # Check for "MUA NGAY" button text
        buy_btn = page.locator(BUY_BUTTON_SELECTOR)
        if await buy_btn.count() > 0 and await buy_btn.is_visible():
             btn_text = await buy_btn.inner_text()
             if "MUA NGAY" in btn_text.upper():
                 ton_kho = "Yes"
    except:
        pass

    # Prices
    gia_khuyen_mai_raw = await get_text_safe(page, PRICE_MAIN_SELECTOR)
    gia_niem_yet_raw = await get_text_safe(page, PRICE_SUB_SELECTOR)
    
    if not gia_niem_yet_raw and gia_khuyen_mai_raw:
        gia_niem_yet_raw = gia_khuyen_mai_raw
    
    # Clean prices
    def clean_price(p):
        if not p: return 0
        return str(p).replace("đ", "").replace("₫", "").replace(".", "").replace(",", "").strip()

    gia_khuyen_mai = clean_price(gia_khuyen_mai_raw)
    gia_niem_yet = clean_price(gia_niem_yet_raw)

    # Promo (Khuyen_Mai)
    khuyen_mai = await get_text_safe(page, PROMO_SELECTOR)
    if khuyen_mai:
        khuyen_mai = re.sub(r'\n+', '\n', khuyen_mai.strip())

    # Payment Promo (Thanh_Toan)
    thanh_toan = await get_text_safe(page, PAYMENT_PROMO_SELECTOR)
    if thanh_toan:
        thanh_toan = re.sub(r'\n+', '\n', thanh_toan.strip())

    # Voucher Image
    voucher_image = ""
    try:
        voucher_el = page.locator(VOUCHER_IMAGE_SELECTOR).first
        if await voucher_el.count() > 0:
            voucher_image = await voucher_el.get_attribute("src")
    except Exception as e:
        print(f"Voucher image extraction failed: {e}")

    # Screenshot
    screenshot_name = ""
    try:
        # Create img_cps directory if it doesn't exist
        img_dir = 'img_cps'
        if not os.path.exists(img_dir):
            os.makedirs(img_dir)

        safe_product_name = re.sub(r'[^\w\-\.]', '_', product_name).strip('. ')
        safe_color = re.sub(r'[^\w\-\.]', '_', str(color_name)).strip('. ')
        timestamp = datetime.now(local_tz).strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{safe_product_name}_{safe_color}_{timestamp}.png"
        full_path = os.path.join(img_dir, filename)
        
        await page.screenshot(path=full_path, full_page=True)
        screenshot_name = filename
    except Exception as e:
        print(f"Screenshot failed: {e}")

    # Prepare Data
    data = {
        "Product_Name": product_name,
        "Color": color_name,
        "Ton_Kho": ton_kho,
        "Gia_Niem_Yet": gia_niem_yet,
        "Gia_Khuyen_Mai": gia_khuyen_mai,
        "Date": date_str,
        "Khuyen_Mai": khuyen_mai,
        "Thanh_Toan": thanh_toan,
        "Link": url,
        "Voucher_Image": voucher_image,
        "screenshot_name": screenshot_name
    }
    
    write_to_csv(csv_path, data)
    print(f"Saved: {product_name} - {color_name} - {gia_khuyen_mai}")

async def main():
    date_str = get_current_date()
    csv_path = setup_csv(date_str)
    
    # Use the global urls_to_process list
    global urls_to_process
    
    print(f"Found {len(urls_to_process)} URLs to process.")
    
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TABS)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=HEADLESS,
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        tasks = [process_url(semaphore, browser, url, csv_path) for url in urls_to_process]
        await asyncio.gather(*tasks)
        
        await browser.close()
    
    print("\n" + "="*50)
    print("🎉 HOÀN THÀNH! 🎉")
    print(f"📂 File kết quả: {csv_path}")
    print(f"🖼️ Thư mục ảnh: img_cps")
    print("-" * 30)
    print("👇 HƯỚNG DẪN TẢI FILE:")
    print("1. Nhìn sang thanh bên trái, bấm vào biểu tượng Thư mục (📁).")
    print("2. Tìm file .csv và thư mục img_cps.")
    print("3. Chuột phải > Download (Tải xuống).")
    print("="*50)

if __name__ == "__main__":
    await main()
