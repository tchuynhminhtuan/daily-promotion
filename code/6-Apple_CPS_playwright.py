import asyncio
import csv
import json
import re
import os
import sys
from datetime import datetime
import pytz
from playwright.async_api import async_playwright, Page
from utils.sites import total_links

# Constants
MAX_CONCURRENT_TABS = int(os.environ.get("MAX_CONCURRENT_TABS", 10))
# Default: Take screenshots = False, Block Images = True
# For GitHub Actions/Proxies: These defaults are now optimized for speed/cost.
TAKE_SCREENSHOT = os.environ.get("TAKE_SCREENSHOT", "False").lower() == "true"
BLOCK_IMAGES = os.environ.get("BLOCK_IMAGES", "True").lower() == "true"

HEADLESS = True 
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

# Selectors for CellphoneS
PRODUCT_NAME_SELECTOR = "h1" # Fallback, usually h1 is good
PRICE_MAIN_SELECTOR = "//div[contains(@class, 'is-flex') and contains(@class, 'is-align-items-center')]/div[contains(@class, 'sale-price')]"
PRICE_SUB_SELECTOR = "//div[contains(@class, 'is-flex') and contains(@class, 'is-align-items-center')]/del[contains(@class, 'base-price')]"
PROMO_SELECTOR = "//div[contains(@class, 'box-product-promotion')]"
PAYMENT_PROMO_SELECTOR = "//div[contains(@class, 'box-more-promotion') and contains(@class, 'my-3')]"
COLOR_OPTIONS_SELECTOR = "//ul[contains(@class, 'list-variants')]/li"
BUY_BUTTON_SELECTOR = "//button[contains(@class, 'btn-cta') and contains(@class, 'order-button') and contains(@class, 'button--large')]"
VOUCHER_IMAGE_SELECTOR = ".box-product-promotion img[alt='voucher']"

def setup_csv(base_path, date_str):
    output_dir = os.path.join(base_path, date_str)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    file_path = os.path.join(output_dir, f"6-cps-{date_str}.csv")
    
    # Create img_cps directory
    img_dir = os.path.join(output_dir, 'img_cps')
    if not os.path.exists(img_dir):
        os.makedirs(img_dir)

    if not os.path.exists(file_path):
        with open(file_path, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=[
                "Product_Name", "Color", "Ton_Kho", "Gia_Niem_Yet", "Gia_Khuyen_Mai",
                 "Date", "Khuyen_Mai", "Thanh_Toan", "Link", "Voucher_Image", "screenshot_name"
            ], delimiter=";")
            writer.writeheader()
    return file_path

def write_to_csv(file_path, data):
    with open(file_path, "a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=[
            "Product_Name", "Color", "Ton_Kho", "Gia_Niem_Yet", "Gia_Khuyen_Mai",
             "Date", "Khuyen_Mai", "Thanh_Toan", "Link", "Voucher_Image", "screenshot_name"
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
        
        # Optimize: Block images to save bandwidth/speed if requested
        if BLOCK_IMAGES:
            await page.route("**/*", lambda route: route.abort() 
                if route.request.resource_type in ["image", "media", "font"] 
                else route.continue_())
        
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
    if TAKE_SCREENSHOT:
        try:
            img_dir = os.path.join(os.path.dirname(csv_path), 'img_cps')
            safe_product_name = re.sub(r'[^\w\-\.]', '_', product_name).strip('. ')
            safe_color = re.sub(r'[^\w\-\.]', '_', str(color_name)).strip('. ')
            timestamp = datetime.now(local_tz).strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"{safe_product_name}_{safe_color}_{timestamp}.png"
            full_path = os.path.join(img_dir, filename)
            
            await page.screenshot(path=full_path, full_page=True)
            screenshot_name = filename
        except Exception as e:
            print(f"Screenshot failed: {e}")
    else:
        screenshot_name = "Disabled"

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
    # Setup
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.join(current_dir, '../content')
    
    local_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    date_str = datetime.now(local_tz).strftime('%Y-%m-%d')
    
    csv_path = setup_csv(base_path, date_str)
    
    # Use the specific URL requested by user for testing
    # urls = ["https://cellphones.com.vn/iphone-air-256gb.html"]
    urls = total_links['cps_urls'] # Uncomment for full run
    print(f"Processing {len(urls)} URL(s).")
    
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TABS)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=HEADLESS,
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        tasks = [process_url(semaphore, browser, url, csv_path) for url in urls]
        await asyncio.gather(*tasks)
        
        await browser.close()

if __name__ == "__main__":
    start_time = datetime.now()
    asyncio.run(main())
    
    duration = datetime.now() - start_time
    seconds = duration.total_seconds()
    print(f"Total execution time: {int(seconds // 3600)} hours {int((seconds % 3600) // 60)} minutes {int(seconds % 60)} seconds")
