import asyncio
import csv
import json
import re
import os
import sys
from datetime import datetime
import pytz
from playwright.async_api import async_playwright, Page
from sites import total_links

# Constants
MAX_CONCURRENT_TABS = 4
HEADLESS = True
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

# Selectors
PRODUCT_NAME_SELECTOR = "h1"
PRICE_CURRENT_SELECTOR = "//div[@class='box-price']/strong" 
PRICE_OLD_SELECTOR = "//div[@class='box-price']/span"
COLOR_OPTIONS_SELECTOR = "//div[contains(@class, 'custom-thumb-transform')]//div[contains(@class, 'item')][.//img]"
STORAGE_OPTIONS_SELECTOR = "//div[contains(text(), 'Lựa chọn phiên bản')]/following-sibling::div//div[contains(@class, 'item')]//a"
STOCK_INDICATOR_SELECTOR = "a.btnQuickOrder" # Check for "MUA NGAY" text
PROMO_SELECTOR = "//div[@id='product-promotion-content']"
PAYMENT_PROMO_SELECTOR = ".promotion-slide-item"

def setup_csv(base_path, date_str):
    output_dir = os.path.join(base_path, date_str)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    file_path = os.path.join(output_dir, f"4-hoangha-{date_str}.csv")
    
    # Create img_hoangha directory
    img_dir = os.path.join(output_dir, 'img_hoangha')
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
        
        try:
            print(f"Processing: {url}")
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)

            # Check for storage options (links)
            # If we want to iterate storage, we should collect them here.
            # For this version, we'll assume the user provides the main link or we just scrape the current page + colors.
            # If we want to be like FPT/MW, we might want to visit other storage links.
            # Let's check if there are other storage options and print them for now, or just focus on colors.
            
            # Color Iteration
            color_btns = page.locator(COLOR_OPTIONS_SELECTOR)
            count = await color_btns.count()
            
            if count > 0:
                print(f"Found {count} color options.")
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

                        print(f"Clicking Color [{i}]: {color_name}", flush=True)
                        
                        # Click logic
                        try:
                            await btn.click(force=True)
                            await page.wait_for_timeout(2000) # Wait for update
                            await scrape_product_data(page, url, csv_path, color_name)
                        except Exception as e:
                            print(f"Failed to click color {i}: {e}")
                    else:
                        pass
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
        # User specified: //div[@id='product-promotion-content']/div
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
                    # The data-promotion is a JSON string inside a list, e.g. [{...}]
                    # It might be HTML encoded, but get_attribute usually returns decoded value.
                    # The user example shows: "[{&quot;IsApplyFlashSale&quot;:false,...}]"
                    # We might need to handle &quot; if it's not automatically decoded.
                    # But usually Playwright handles it.
                    # Let's try to parse it.
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
        print(f"Error extracting payment promo: {e}")

    # Screenshot
    screenshot_name = ""
    try:
        img_dir = os.path.join(os.path.dirname(csv_path), 'img_hoangha')
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
    
    # urls = ["https://hoanghamobile.com/dien-thoai/iphone-17-pro-max"]
    urls = total_links['hh_urls']
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
    asyncio.run(main())
