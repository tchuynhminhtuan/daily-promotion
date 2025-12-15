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
# @markdown Sau đó bấm nút **Play** (hình tam giác).

import asyncio
import csv
import json
import re
import os
import sys
from datetime import datetime
import pytz
from playwright.async_api import async_playwright, Page

# --- Cấu hình Input ---
ds_link = "
https://hoanghamobile.com/dien-thoai/iphone-17-pro-max
https://hoanghamobile.com/laptop/macbook-air-m4-13-6-inch-16gb-256gb
https://hoanghamobile.com/may-tinh-bang/may-tinh-bang-redmagic-astra-gaming-12gb-256gb-chinh-hang,
https://hoanghamobile.com/may-tinh-bang/ipad-air-m3-11-inch-wifi-128gb,
https://hoanghamobile.com/tai-nghe/tai-nghe-airpods-pro-3-chinh-hang-apple-viet-nam " #@param {type:"string"}

# ==============================================================================
# XỬ LÝ DỮ LIỆU
# ==============================================================================

# Tách link từ input form
raw_links = ds_link.replace(' ', ',').replace('\n', ',').split(',')
hh_urls = [link.strip() for link in raw_links if link.strip()]

if not hh_urls:
    print("⚠️ LƯU Ý: Bạn chưa nhập link nào cả. Hãy dán link vào ô 'ds_link' ở trên.")
else:
    print(f"📋 Đã nhận {len(hh_urls)} link cần xử lý.")

# --- Cấu hình Crawler ---
MAX_CONCURRENT_TABS = 3
HEADLESS = True
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

# --- Các thành phần web (Selectors từ Hoang Ha) ---
PRODUCT_NAME_SELECTOR = "h1"
PRICE_CURRENT_SELECTOR = "//div[@class='box-price']/strong" 
PRICE_OLD_SELECTOR = "//div[@class='box-price']/span"
COLOR_OPTIONS_SELECTOR = "//div[contains(@class, 'custom-thumb-transform')]//div[contains(@class, 'item')][.//img]"
STOCK_INDICATOR_SELECTOR = "a.btnQuickOrder" # Check for "MUA NGAY" text
PROMO_SELECTOR = "//div[@id='product-promotion-content']"
PAYMENT_PROMO_SELECTOR = ".promotion-slide-item"

def setup_csv(date_str):
    # Tạo file kết quả csv
    file_path = f"hoangha-{date_str}.csv"
    
    # Tạo thư mục chứa ảnh
    img_dir = 'img_hoangha'
    if not os.path.exists(img_dir):
        os.makedirs(img_dir)

    if not os.path.exists(file_path):
        with open(file_path, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=[
                "Product_Name", "Color", "Ton_Kho", "Gia_Niem_Yet", "Gia_Khuyen_Mai",
                 "Date", "Khuyen_Mai", "Thanh_Toan", "Link", "screenshot_name"
            ], delimiter=";")
            writer.writeheader()
    return file_path

def write_to_csv(file_path, data):
    with open(file_path, "a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=[
            "Product_Name", "Color", "Ton_Kho", "Gia_Niem_Yet", "Gia_Khuyen_Mai",
             "Date", "Khuyen_Mai", "Thanh_Toan", "Link", "screenshot_name"
        ], delimiter=";")
        writer.writerow(data)

async def get_text_safe(page, selector, timeout=2000):
    try:
        if await page.locator(selector).count() > 0:
            if await page.locator(selector).first.is_visible(timeout=timeout):
                return await page.locator(selector).first.inner_text()
        return ""
    except Exception:
        return ""

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
            print(f"🔄 Đang xử lý: {url}")
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)

            # Color Iteration
            color_btns = page.locator(COLOR_OPTIONS_SELECTOR)
            count = await color_btns.count()
            
            if count > 0:
                print(f"Tìm thấy {count} lựa chọn màu.")
                for i in range(count):
                    # Re-locate to avoid stale elements
                    color_btns = page.locator(COLOR_OPTIONS_SELECTOR)
                    btn = color_btns.nth(i)
                    
                    # Skip visibility check, just try to get text and click
                    color_name = await btn.text_content()
                    
                    if color_name:
                        # Clean color name
                        color_name = color_name.strip().split('\n')[0].strip()
                        color_name = re.sub(r'\d{1,3}(\.\d{3})*(\s)*[đ₫]', '', color_name).strip()
                        
                        if not color_name:
                            continue

                        if len(color_name) > 30:
                            continue
                            
                        if any(x in color_name for x in ["Samsung", "iPhone", "GB", "TB", "/"]):
                            continue

                        print(f"Click vào màu [{i}]: {color_name}", flush=True)
                        
                        # Click logic
                        try:
                            await btn.click(force=True)
                            await page.wait_for_timeout(2000) # Wait for update
                            await scrape_product_data(page, url, csv_path, color_name)
                        except Exception as e:
                            print(f"Không thể click màu {i}: {e}")
                    else:
                        pass
            else:
                print("ℹ️ Không tìm thấy lựa chọn màu. Lấy dữ liệu trang hiện tại.")
                await scrape_product_data(page, url, csv_path, "Unknown")

        except Exception as e:
            print(f"❌ Lỗi khi xử lý {url}: {e}")
        finally:
            await page.close()

async def scrape_product_data(page, url, csv_path, color_name):
    # Time setup
    local_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    now_utc = datetime.now(pytz.utc)
    date_str = now_utc.astimezone(local_tz).strftime('%Y-%m-%d')

    # Product Name
    product_name = await get_text_safe(page, PRODUCT_NAME_SELECTOR)
    product_name = product_name.strip().split(" - ")[0]

    # Stock (Ton_Kho)
    ton_kho = "No"
    try:
        buy_btn_text = await get_text_safe(page, STOCK_INDICATOR_SELECTOR)
        if "MUA NGAY" in buy_btn_text:
            ton_kho = "Yes"
    except:
        pass

    # Prices
    gia_khuyen_mai_raw = await get_text_safe(page, PRICE_CURRENT_SELECTOR)
    gia_niem_yet_raw = await get_text_safe(page, PRICE_OLD_SELECTOR)
    
    if not gia_niem_yet_raw and gia_khuyen_mai_raw:
        gia_niem_yet_raw = gia_khuyen_mai_raw
    
    # Clean prices
    def clean_price(p):
        if not p: return 0
        return str(p).replace("đ", "").replace("₫", "").replace(".", "").replace(",", "").strip()

    gia_khuyen_mai = clean_price(gia_khuyen_mai_raw)
    gia_niem_yet = clean_price(gia_niem_yet_raw)

    # Promo (Khuyen_Mai)
    khuyen_mai = ""
    try:
        # Try to get text from commitment/promo section
        # Updated selector: //div[@id='product-promotion-content']/div
        promos = page.locator(f"{PROMO_SELECTOR}/div")
        if await promos.count() > 0:
            texts = await promos.all_inner_texts()
            khuyen_mai = "\n".join([t.strip() for t in texts if t.strip()])
    except:
        pass

    # Payment Promo (Thanh_Toan)
    thanh_toan = ""
    try:
        # Extract from data-promotion attribute
        promo_items = page.locator(PAYMENT_PROMO_SELECTOR)
        count = await promo_items.count()
        promo_texts = []
        for i in range(count):
            data_promo = await promo_items.nth(i).get_attribute("data-promotion")
            if data_promo:
                try:
                    promos_list = json.loads(data_promo)
                    if isinstance(promos_list, list):
                        for p in promos_list:
                            if "Title" in p:
                                promo_texts.append(p["Title"])
                except json.JSONDecodeError:
                    pass
        
        if promo_texts:
            thanh_toan = "\n".join(promo_texts)
    except Exception as e:
        print(f"Lỗi khi lấy khuyến mãi thanh toán: {e}")

    # Screenshot
    screenshot_name = ""
    try:
        img_dir = 'img_hoangha'
        safe_product_name = re.sub(r'[^\w\-\.]', '_', product_name).strip('. ')
        safe_color = re.sub(r'[^\w\-\.]', '_', str(color_name)).strip('. ')
        timestamp = datetime.now(local_tz).strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{safe_product_name}_{safe_color}_{timestamp}.png"
        full_path = os.path.join(img_dir, filename)
        
        await page.screenshot(path=full_path, full_page=True)
        screenshot_name = filename
    except Exception as e:
        print(f"⚠️ Chụp ảnh màn hình thất bại: {e}")

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
        "screenshot_name": screenshot_name
    }
    
    write_to_csv(csv_path, data)
    print(f"✅ Đã lưu: {product_name} - {color_name} - {gia_khuyen_mai}")

async def main():
    if not hh_urls:
        return

    local_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    date_str = datetime.now(local_tz).strftime('%Y-%m-%d')
    
    csv_path = setup_csv(date_str)
    
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TABS)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=HEADLESS,
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        tasks = [process_url(semaphore, browser, url, csv_path) for url in hh_urls]
        await asyncio.gather(*tasks)
        
        await browser.close()
    
    print("\n" + "="*50)
    print("🎉 HOÀN THÀNH! 🎉")
    print(f"📂 File kết quả: {csv_path}")
    print(f"🖼️ Thư mục ảnh: img_hoangha")
    print("-" * 30)
    print("👇 HƯỚNG DẪN TẢI FILE:")
    print("1. Nhìn sang thanh bên trái, bấm vào biểu tượng Thư mục (📁).")
    print("2. Tìm file .csv và thư mục img_hoangha.")
    print("3. Chuột phải > Download (Tải xuống).")
    print("="*50)

# Chạy chương trình
if hh_urls:
    await main()
