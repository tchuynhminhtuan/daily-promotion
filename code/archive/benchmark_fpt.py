import asyncio
import csv
import json
import re
import os
import sys
import time
from datetime import datetime
import pytz
from playwright.async_api import async_playwright, Page
# Removed sites import to avoid dependency
import pandas as pd

# Constants
MAX_CONCURRENT_TABS = 4
HEADLESS = True 
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

# Selectors
PRODUCT_NAME_SELECTOR = "//h1[contains(@class, 'text-textOnWhitePrimary')]"
PRICE_MAIN_SELECTOR = "//span[contains(@class, 'text-black-opacity-100 h4-bold')]"
PRICE_SUB_SELECTOR = "//span[contains(@class, 'text-neutral-gray-5 line-through')]"
PROMO_SELECTOR = "//div[contains(@class, 'mt-2 flex flex-col gap-2')]"
THANH_TOAN_SELECTOR = "//div[@class='flex h-max w-full flex-col gap-3 p-4']"
THANH_TOAN_BTN_SELECTOR = "(//div[contains(@class, 'flex flex-col overflow-hidden bg-white')])[2]/div/button"
OTHER_PROMO_SELECTOR = "(//div[contains(@class, 'flex flex-col overflow-hidden bg-white')])[1]"
OTHER_PROMO_BTN_SELECTOR = "(//div[contains(@class, 'flex flex-col overflow-hidden bg-white')])[1]/div/button"
STORAGE_OPTIONS_XPATH = "(//div[contains(@class, 'flex flex-wrap gap-2')])[1]/div//button"
COLOR_OPTIONS_XPATH = "(//div[contains(@class, 'flex flex-wrap gap-2')])[2]/div//button"
COLOR_SELECTOR_INDICATOR = "//span[contains(text(), 'Màu')]/following-sibling::div//button[descendant::span[contains(@class, 'Selection_triangle__csu2Y')]]"
BUY_BUTTON_SELECTOR = "//div[@id='detail-buying-btns']/button[2]"
NOTI_SELECTOR = ".st-stt__noti"

def setup_csv(base_path, date_str):
    output_dir = os.path.join(base_path, date_str)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    file_path = os.path.join(output_dir, f"benchmark-fpt-{date_str}.csv")
    img_dir = os.path.join(output_dir, 'img_fpt_bench')
    if not os.path.exists(img_dir):
        os.makedirs(img_dir)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass
    with open(file_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=[
            "Product_Name", "Color", "Ton_Kho", "Gia_Niem_Yet", "Gia_Khuyen_Mai",
             "Date", "Khuyen_Mai", "Thanh_Toan", "Other_promotion", "Link", "screenshot_name"
        ], delimiter=";")
        writer.writeheader()
    return file_path

async def write_to_csv(file_path, data, lock):
    async with lock:
        with open(file_path, "a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=[
                "Product_Name", "Color", "Ton_Kho", "Gia_Niem_Yet", "Gia_Khuyen_Mai",
                 "Date", "Khuyen_Mai", "Thanh_Toan", "Other_promotion", "Link", "screenshot_name"
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

async def click_and_get_text(page, container_selector, button_selector):
    try:
        btn = page.locator(button_selector).first
        if await btn.count() > 0 and await btn.is_visible():
            try:
                # print(f"Clicking button: {button_selector}")
                await btn.click()
                await page.wait_for_timeout(1000) 
            except Exception as e:
                print(f"Error clicking button {button_selector}: {e}")
        return await get_text_safe(page, container_selector)
    except Exception:
        return ""

async def wait_for_overlay(page):
    try:
        overlay = page.locator(".bg-black-opacity-70")
        if await overlay.count() > 0 and await overlay.is_visible():
            # print("Waiting for overlay to disappear...")
            await overlay.wait_for(state="hidden", timeout=5000)
    except Exception as e:
        pass

async def handle_popup(page):
    try:
        de_sau_btn = page.locator("button").filter(has_text="Để sau")
        if await de_sau_btn.count() > 0 and await de_sau_btn.is_visible():
            # print("Found 'Để sau' popup, clicking...")
            await de_sau_btn.click()
            await page.wait_for_timeout(1000)
    except Exception as e:
        pass

async def process_url(semaphore, browser, url, csv_path, csv_lock):
    async with semaphore:
        start_time = time.time()
        page = await browser.new_page(
            user_agent=USER_AGENT,
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1,
        )
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        try:
            print(f"Processing: {url}")
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000) 
            await handle_popup(page)
            await process_storage_options(page, url, csv_path, csv_lock)
            
            duration = time.time() - start_time
            print(f"Finished {url} in {duration:.2f}s")
        except Exception as e:
            print(f"Error processing {url}: {e}")
        finally:
            await page.close()

async def process_storage_options(page, url, csv_path, csv_lock):
    storage_container_xpath = "(//div[contains(@class, 'flex flex-wrap gap-2')])[1]"
    storage_links = page.locator(f"{storage_container_xpath}//a")
    link_count = await storage_links.count()

    if link_count > 0:
        # Simplified: Just log that we would iterate
        # In benchmark, let's just process the current page as if it's one variant to save time/complexity
        # Or just pick the first link if we want strictly similar behavior
        print(f"Found {link_count} storage links. For benchmark, checking current page colors only.")
        await process_color_options(page, url, csv_path, csv_lock)
    else:
        storage_btns_xpath = f"{storage_container_xpath}/div//button"
        storage_btns = page.locator(storage_btns_xpath)
        count = await storage_btns.count()
        
        if count == 0:
            await process_color_options(page, url, csv_path, csv_lock)
        else:
            # For benchmark, process only FIRST storage option to be faster
            # print(f"Found {count} storage buttons. processing first one only.")
            for i in range(min(1, count)):
                storage_btns = page.locator(storage_btns_xpath)
                btn = storage_btns.nth(i)
                await wait_for_overlay(page)
                await handle_popup(page)
                if await btn.is_visible():
                    txt = await btn.text_content()
                    name = txt.strip()
                    try:
                        await btn.evaluate("node => node.click()")
                        await page.wait_for_timeout(1000)
                        await handle_popup(page)
                        is_storage = "GB" in name or "TB" in name
                        potential_color = None
                        if not is_storage: potential_color = name
                        await process_color_options(page, url, csv_path, csv_lock, parent_color=potential_color)
                    except Exception as e:
                        print(f"Error clicking storage {i}: {e}")

async def process_color_options(page, url, csv_path, csv_lock, parent_color=None):
    color_container_xpath = "(//div[contains(@class, 'flex flex-wrap gap-2')])[2]"
    color_btns_xpath = f"{color_container_xpath}/div//button"
    color_btns = page.locator(color_btns_xpath)
    count = await color_btns.count()
    
    if count > 0:
        print(f"Found {count} color buttons.")
        # Process ALL colors to measure real impact of screenshotting
        for i in range(count):
            color_btns = page.locator(color_btns_xpath)
            btn = color_btns.nth(i)
            await wait_for_overlay(page)
            await handle_popup(page)
            if await btn.is_visible():
                txt = await btn.text_content()
                color_name = txt.strip()
                try:
                    start_color = time.time()
                    await btn.evaluate("node => node.click()")
                    await page.wait_for_timeout(1500)
                    await handle_popup(page)
                    await scrape_product_data(page, url, csv_path, csv_lock, forced_color=color_name)
                    print(f"  Color {color_name} took {time.time() - start_color:.2f}s")
                except Exception as e:
                    print(f"Error clicking color {i}: {e}")
    else:
        await scrape_product_data(page, url, csv_path, csv_lock, forced_color=parent_color)

async def scrape_product_data(page, url, csv_path, csv_lock, forced_color=None):
    local_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    
    # Simulate processing time
    product_name = await get_text_safe(page, PRODUCT_NAME_SELECTOR)
    if not product_name:
        try: product_name = await page.locator(".st-name").text_content()
        except: product_name = "Unknown"
    
    # ... (other extractions omitted for brevity, keeping heavy items) ...
    
    # Screenshot - The heavy part
    try:
        img_dir = os.path.join(os.path.dirname(csv_path), 'img_fpt_bench')
        safe_product_name = re.sub(r'[^\w\-\.]', '_', product_name).strip('. ')
        # timestamp = datetime.now(local_tz).strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"bench_{safe_product_name}_{forced_color}.png"
        full_path = os.path.join(img_dir, filename)
        
        # Benchmark screenshot only
        t0 = time.time()
        await page.screenshot(path=full_path, full_page=True)
        # print(f"    Screenshot took {time.time() - t0:.2f}s")
    except Exception as e:
        print(f"Screenshot failed: {e}")

    await write_to_csv(csv_path, {"Product_Name": product_name, "Link": url}, csv_lock)

async def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.join(current_dir, '../content')
    local_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    date_str = "benchmark" # Use specific folder
    csv_path = setup_csv(base_path, date_str)
    csv_lock = asyncio.Lock()
    
    urls = [
        'https://fptshop.com.vn/dien-thoai/iphone-15',
        'https://fptshop.com.vn/may-tinh-xach-tay/macbook-air-m2-2023-15-inch',
        'https://fptshop.com.vn/smartwatch/apple-watch-se-3-gps-40mm-vien-nhom-day-cao-su'
    ]
    
    print(f"Starting benchmark on {len(urls)} URLs...")
    t_start = time.time()
    
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TABS)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS)
        tasks = [process_url(semaphore, browser, url, csv_path, csv_lock) for url in urls]
        await asyncio.gather(*tasks)
        await browser.close()
        
    print(f"Total benchmark time: {time.time() - t_start:.2f}s")

if __name__ == "__main__":
    asyncio.run(main())
