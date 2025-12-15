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
default_mw_urls = [
    'https://www.thegioididong.com/dtdd/iphone-17-pro-max',
    'https://www.thegioididong.com/dtdd/iphone-17-pro',
    'https://www.thegioididong.com/dtdd/iphone-air',
    'https://www.thegioididong.com/dtdd/iphone-17',
    'https://www.thegioididong.com/dtdd/iphone-16-pro-max',
    'https://www.thegioididong.com/dtdd/iphone-16',
    'https://www.thegioididong.com/dtdd/iphone-16e',
    'https://www.thegioididong.com/dtdd/iphone-15',
    'https://www.thegioididong.com/dtdd/iphone-15-plus',
    'https://www.thegioididong.com/dtdd/iphone-13',
    'https://www.thegioididong.com/dtdd/iphone-14',
    'https://www.thegioididong.com/dtdd/iphone-16-plus',
    'https://www.thegioididong.com/dtdd/iphone-16-pro',
    'https://www.thegioididong.com/dong-ho-thong-minh/apple-watch-series-11-42mm-vien-nhom-day-the-thao',
    'https://www.thegioididong.com/dong-ho-thong-minh/apple-watch-series-11-46mm-vien-nhom-day-the-thao',
    'https://www.thegioididong.com/dong-ho-thong-minh/apple-watch-series-11-gps-cellular-42mm-vien-titanium-day-milan',
    'https://www.thegioididong.com/dong-ho-thong-minh/apple-watch-series-11-gps-cellular-42mm-vien-nhom-day-the-thao',
    'https://www.thegioididong.com/dong-ho-thong-minh/apple-watch-series-11-gps-cellular-46mm-vien-nhom-day-the-thao',
    'https://www.thegioididong.com/dong-ho-thong-minh/apple-watch-series-11-gps-cellular-42m-vien-titanium-day-the-thao',
    'https://www.thegioididong.com/dong-ho-thong-minh/apple-watch-series-11-gps-cellular-46mm-vien-titanium-day-milan',
    'https://www.thegioididong.com/dong-ho-thong-minh/apple-watch-series-11-gps-cellular-46mm-vien-titanium-day-the-thao',
    'https://www.thegioididong.com/dong-ho-thong-minh/apple-watch-ultra-3-gps-cellular-49mm-vien-titanium-day-ocean',
    'https://www.thegioididong.com/dong-ho-thong-minh/apple-watch-ultra-3-gps-cellular-49mm-vien-titanium-day-milan',
    'https://www.thegioididong.com/dong-ho-thong-minh/apple-watch-ultra-3-gps-cellular-49mm-vien-titanium-day-alpine',
    'https://www.thegioididong.com/dong-ho-thong-minh/apple-watch-ultra-3-gps-cellular-49mm-vien-titanium-day-trail',
    'https://www.thegioididong.com/dong-ho-thong-minh/apple-watch-se-3-40mm-vien-nhom-day-the-thao',
    'https://www.thegioididong.com/dong-ho-thong-minh/apple-watch-se-3-gps-cellular-40mm-vien-nhom-day-the-thao',
    'https://www.thegioididong.com/dong-ho-thong-minh/apple-watch-se-3-44mm-vien-nhom-day-the-thao',
    'https://www.thegioididong.com/dong-ho-thong-minh/apple-watch-se-3-gps-cellular-44mm-vien-nhom-day-the-thao',
    'https://www.thegioididong.com/dong-ho-thong-minh/apple-watch-s10-lte-46mm-vien-titanium-day-thep',
    'https://www.thegioididong.com/dong-ho-thong-minh/apple-watch-series-10-42mm-day-vai',
    'https://www.thegioididong.com/dong-ho-thong-minh/apple-watch-series-10-46mm-day-vai',
    'https://www.thegioididong.com/dong-ho-thong-minh/apple-watch-series-10-lte-42mm-day-vai',
    'https://www.thegioididong.com/dong-ho-thong-minh/apple-watch-series-10-lte-46mm-day-vai',
    'https://www.thegioididong.com/dong-ho-thong-minh/apple-watch-s10-lte-46mm-vien-titanium-day-the-thao',
    'https://www.thegioididong.com/dong-ho-thong-minh/apple-watch-s10-lte-46mm',
    'https://www.thegioididong.com/dong-ho-thong-minh/apple-watch-s10-lte-42mm-vien-titanium-day-the-thao',
    'https://www.thegioididong.com/dong-ho-thong-minh/apple-watch-se-2-40mm-vien-nhom-day-silicone',
    'https://www.thegioididong.com/dong-ho-thong-minh/apple-watch-se-2-44mm-vien-nhom-day-silicone',
    'https://www.thegioididong.com/dong-ho-thong-minh/apple-watch-se-2-44mm-vien-nhom-day-vai',
    'https://www.thegioididong.com/dong-ho-thong-minh/apple-watch-se-2-2023-lte-40mm-vien-nhom-day-vai',
    'https://www.thegioididong.com/laptop/macbook-air-13-inch-m4-16gb-256gb',
    'https://www.thegioididong.com/laptop/apple-macbook-air-m2-2022-16gb-256gb',
    'https://www.thegioididong.com/laptop/macbook-air-13-inch-m4-16gb-512gb',
    'https://www.thegioididong.com/laptop/macbook-air-15-inch-m4-16gb-256gb',
    'https://www.thegioididong.com/laptop/macbook-air-15-inch-m4-16gb-512gb',
    'https://www.thegioididong.com/laptop/macbook-air-13-inch-m4-16gb-256gb-sac-70w',
    'https://www.thegioididong.com/laptop/macbook-air-13-inch-m4-24gb-512gb',
    'https://www.thegioididong.com/laptop/macbook-air-15-inch-m4-24gb-512gb',
    'https://www.thegioididong.com/laptop/macbook-air-13-inch-m4-32gb-256gb',
    'https://www.thegioididong.com/laptop/macbook-pro-14-inch-m4-pro-24gb-512gb',
    'https://www.thegioididong.com/laptop/macbook-pro-14-nano-m4-pro-24-512',
    'https://www.thegioididong.com/laptop/macbook-pro-16-inch-m4-pro-24gb-512gb',
    'https://www.thegioididong.com/laptop/macbook-pro-14-inch-m4-pro-48gb-1tb',
    'https://www.thegioididong.com/laptop/macbook-pro-14-inch-m4-pro-24gb-1tb',
    'https://www.thegioididong.com/laptop/macbook-pro-14-inch-m4-pro-48gb-512gb',
]

# Xử lý input
if ds_link.strip():
    raw_links = ds_link.replace(' ', ',').replace('\n', ',').split(',')
    urls_to_process = [link.strip() for link in raw_links if link.strip()]
    print(f"📋 Đang chạy danh sách tùy chỉnh ({len(urls_to_process)} link).")
else:
    urls_to_process = list(default_mw_urls)
    print(f"📋 Đang chạy danh sách mặc định ({len(urls_to_process)} link).")


# --- Configuration ---
MAX_CONCURRENT_TABS = 4
HEADLESS = True
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# --- Selectors ---
SHOCK_PRICE_SELECTORS = [
    ".bs_price strong",
    "//div[@class='bc_title']/div/strong",
    ".oo-left strong"
]

SHOCK_PRICE_OLD_SELECTORS = [
    ".bs_price em",
    "//div[@class='bc_title']/div/em",
    ".oo-left em"
]

REGULAR_PRICE_SELECTORS = [
    ".giamsoc-ol-price",
    ".box-price-present",
    ".center b",
    "//ul[@class='prods-price']/li//span"
]

OLD_PRICE_SELECTORS = [
    ".box-price-old",
    ".box-price-present",
    ".center b",
    "//ul[@class='prods-price']/li//del"
]

PRODUCT_NAME_SELECTORS = [
    "h1",
    "//ul[@class='breadcrumb']/li[last()]"
]

PROMO_SELECTORS = [
    "//div[@class='bs_content']/div[@class='block__promo']",
    ".block__promo",
    ".promotions"
]

UU_DAI_THEM_SELECTORS = [
    "//div[@class='bs_content']/div[@class='campaign c4 dt']",
    ".campaign.c4.dt"
]

STORE_AVAILABILITY_SELECTORS = [
    "//a[@class='store jsSpmarket']",
    ".store.jsSpmarket"
]

STORAGE_OPTION_SELECTORS = [
    "a.box03__item.item"
]

COLOR_SELECTORS = [
    ".box03.color .item.act",
    ".box03.color .item.check"
]

# --- Helper Functions ---
async def get_text_safe(page, selectors):
    """Iterates through selectors and returns the text of the first match."""
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            # Use text_content() to get text even if hidden, as some valid price elements are hidden
            text = await locator.text_content(timeout=1000)
            if text and text.strip():
                return text.strip()
        except Exception:
            continue
    return None

async def get_formatted_text_safe(page, selectors):
    """Iterates through selectors and returns the inner text of the first match, preserving formatting."""
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            # Use inner_text() to preserve visual formatting (newlines)
            text = await locator.inner_text(timeout=1000)
            if text and text.strip():
                return text.strip()
        except Exception:
            continue
    return None

def get_current_date():
    tz = pytz.timezone('Asia/Ho_Chi_Minh')
    return datetime.now(tz).strftime("%Y-%m-%d")

def setup_csv(date_str):
    # Output directly to current directory in Colab
    file_path = f"2-mw-{date_str}.csv"
    
    # Create file with header if it doesn't exist
    if not os.path.exists(file_path) or os.stat(file_path).st_size == 0:
        with open(file_path, "w", newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=[
                "Product_Name", "Color", "Ton_Kho", "Gia_Niem_Yet", "Gia_Khuyen_Mai",
                # "Chien_Gia", '+VNPAY', "Store_Chien",
               "Date", "Khuyen_Mai", "Uu_Dai_Them", "Link", 'screenshot_name'
            ], delimiter=";")
            writer.writeheader()
    return file_path

def write_to_csv(file_path, data):
    with open(file_path, "a", newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=[
            "Product_Name", "Color", "Ton_Kho", "Gia_Niem_Yet", "Gia_Khuyen_Mai",
            # "Chien_Gia", '+VNPAY', "Store_Chien",
             "Date", "Khuyen_Mai", "Uu_Dai_Them", "Link", 'screenshot_name'
        ], delimiter=";")
        writer.writerow(data)

# --- Main Logic ---
async def process_url(context, url, semaphore, csv_path, date_str):
    discovered_urls = []
    async with semaphore:
        page = await context.new_page()
        print(f"Processing: {url}")
        
        data = {
            "Product_Name": "", "Color": "", "Ton_Kho": "0", "Gia_Niem_Yet": "0", "Gia_Khuyen_Mai": "0",
            # "Chien_Gia": "", '+VNPAY': "", "Store_Chien": "MW",
             "Date": date_str, "Khuyen_Mai": "", "Uu_Dai_Them": "", "Link": url, 'screenshot_name': ""
        }

        try:
            await page.goto(url, timeout=60000)
            
            # Wait for price element to load
            try:
                # Try to wait for any of the common price selectors
                common_selectors = [".box-price-present", ".price-present", ".box-price", ".giamsoc-ol-price"]
                combined_selector = ", ".join(common_selectors)
                # Wait for attached state as elements might be present but hidden
                await page.wait_for_selector(combined_selector, timeout=10000, state='attached')
            except Exception as e:
                print(f"Warning: Price element not found for {url} within timeout. Error: {e}")

            # 0. Discover other storage options
            try:
                storage_elements = await page.locator(STORAGE_OPTION_SELECTORS[0]).all()
                for element in storage_elements:
                    href = await element.get_attribute("href")
                    if href:
                        full_url = "https://www.thegioididong.com" + href if href.startswith("/") else href
                        discovered_urls.append(full_url)
            except Exception as e:
                print(f"Warning: Could not extract storage options for {url}: {e}")

            # 1. Product Name
            product_name = await get_text_safe(page, PRODUCT_NAME_SELECTORS)
            if product_name:
                product_name = product_name.strip().replace("Mini", "mini")
                to_remove = ["Điện thoại ", "Máy tính bảng ", "Laptop Apple ", "Tai nghe chụp tai Bluetooth ", "Tai nghe Bluetooth "]
                for item in to_remove:
                    product_name = product_name.replace(item, "")
                data["Product_Name"] = product_name
            else:
                data["Product_Name"] = "Unknown Product"

            # 2. Price Logic
            shock_price = await get_text_safe(page, SHOCK_PRICE_SELECTORS)
            if shock_price:
                gia_soc = shock_price.replace(" *", "").replace(".", "").replace("₫", "").strip()
                data["Gia_Khuyen_Mai"] = gia_soc + "soc"
                old_price = await get_text_safe(page, SHOCK_PRICE_OLD_SELECTORS)
                if old_price:
                    data["Gia_Niem_Yet"] = old_price.replace(" *", "").replace(".", "").replace("₫", "").strip()
            else:
                reg_price = await get_text_safe(page, REGULAR_PRICE_SELECTORS)
                if reg_price:
                    data["Gia_Khuyen_Mai"] = reg_price.replace("Giá dự kiến: ", "").replace("Giá bán:", "").replace("*", "").replace(".", "").replace("₫", "").strip()
                
                old_price = await get_text_safe(page, OLD_PRICE_SELECTORS)
                if old_price:
                    data["Gia_Niem_Yet"] = old_price.replace("Giá dự kiến: ", "").replace("Giá bán:", "").replace(".", "").replace("₫", "").strip()

            # 3. Stock Status (Ton_Kho)
            # If we found a price, assume in stock (1), unless explicitly out of stock
            if data["Gia_Khuyen_Mai"] != "0" or data["Gia_Niem_Yet"] != "0":
                data["Ton_Kho"] = "Yes"
            else:
                data["Ton_Kho"] = "No"
            
            # 4. Promotion Info (Khuyen_Mai)
            promo_text = await get_formatted_text_safe(page, PROMO_SELECTORS)
            if promo_text:
                # Clean up the text: remove extra newlines and spaces, preserve meaningful line breaks
                lines = [line.strip() for line in promo_text.splitlines() if line.strip()]
                cleaned_promo = "\n".join(lines)
                data["Khuyen_Mai"] = cleaned_promo

            # 5. Additional Offers (Uu_Dai_Them)
            uu_dai_text = await get_formatted_text_safe(page, UU_DAI_THEM_SELECTORS)
            if uu_dai_text:
                # Clean up the text: remove extra newlines and spaces, preserve meaningful line breaks
                lines = [line.strip() for line in uu_dai_text.splitlines() if line.strip()]
                cleaned_uu_dai = "\n".join(lines)
                data["Uu_Dai_Them"] = cleaned_uu_dai

            # 6. Color
            color_text = await get_text_safe(page, COLOR_SELECTORS)
            if color_text:
                data["Color"] = color_text

            # 6. Screenshot Capture
            try:
                # Create img_mw directory if it doesn't exist
                img_dir = 'img_mw'
                if not os.path.exists(img_dir):
                    os.makedirs(img_dir)

                # Sanitize product name for filename
                safe_product_name = re.sub(r'[^\w\-\.]', '_', data['Product_Name']).strip('. ')
                
                # Generate timestamp
                tz = pytz.timezone('Asia/Ho_Chi_Minh')
                timestamp = datetime.now(tz).strftime("%Y-%m-%d_%H-%M-%S")
                
                filename = f"{safe_product_name}_{timestamp}.png"
                full_path = os.path.join(img_dir, filename)
                
                # Set viewport size for better capture (optional, but good for full page details)
                await page.set_viewport_size({"width": 1920, "height": 2080})
                
                # Take screenshot
                await page.screenshot(path=full_path, full_page=True)
                
                # Save just the filename to CSV
                data['screenshot_name'] = filename
                
            except Exception as e:
                print(f"Warning: Could not take screenshot for {url}: {e}")

            print(f"Done: {data['Product_Name']} - {data['Gia_Khuyen_Mai']}")
            write_to_csv(csv_path, data)

        except Exception as e:
            print(f"Error processing {url}: {e}")
        finally:
            await page.close()
            return discovered_urls

async def main():
    date_str = get_current_date()
    csv_path = setup_csv(date_str)
    
    # Use the global urls_to_process list
    global urls_to_process
    
    print(f"Found {len(urls_to_process)} initial URLs to process.")
    
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TABS)
    
    visited_urls = set()
    # Create a local queue from the global list
    queue = list(urls_to_process)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=HEADLESS,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1280, "height": 720}
        )
        
        while queue:
            # Process in batches to manage concurrency and dynamic addition
            current_batch = []
            while queue and len(current_batch) < MAX_CONCURRENT_TABS * 2: # Buffer a bit more than max tabs
                url = queue.pop(0)
                if url not in visited_urls:
                    visited_urls.add(url)
                    current_batch.append(url)
            
            if not current_batch:
                continue

            tasks = [process_url(context, url, semaphore, csv_path, date_str) for url in current_batch]
            results = await asyncio.gather(*tasks)
            
            # Add discovered URLs to queue
            for discovered_list in results:
                for url in discovered_list:
                    if url not in visited_urls and url not in queue:
                         # Optional: Filter to ensure it's a relevant product link if needed
                         queue.append(url)
        
        await browser.close()
    
    print("\n" + "="*50)
    print("🎉 HOÀN THÀNH! 🎉")
    print(f"📂 File kết quả: {csv_path}")
    print(f"🖼️ Thư mục ảnh: img_mw")
    print("-" * 30)
    print("👇 HƯỚNG DẪN TẢI FILE:")
    print("1. Nhìn sang thanh bên trái, bấm vào biểu tượng Thư mục (📁).")
    print("2. Tìm file .csv và thư mục img_mw.")
    print("3. Chuột phải > Download (Tải xuống).")
    print("="*50)

if __name__ == "__main__":
    start_time = datetime.now()
    await main()
    print(f"Total execution time: {datetime.now() - start_time}")
