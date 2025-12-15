import asyncio
import csv
import json
import re
import os
import sys
import random
import time
from datetime import datetime
import pytz
from playwright.async_api import async_playwright, Page
from sites import total_links
import pandas as pd

# Try to import fake_useragent, else fallback
try:
    from fake_useragent import UserAgent
    ua = UserAgent()
    HAS_FAKE_UA = True
except ImportError:
    HAS_FAKE_UA = False
    # Robust fallback list
    USER_AGENT_LIST = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    ]

# Constants
MAX_CONCURRENT_TABS = 6 # Reduced slightly to prevent resource choking with screenshots
USE_SMART_WAIT = True
SCREENSHOT_STRATEGY = "FIRST_ONLY"
HEADLESS = True

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
COLOR_SELECTOR_INDICATOR = "//span[contains(text(), 'Màu')]/following-sibling::div//button[descendant::span[contains(@class, 'Selection_triangle__csu2Y')]]"
BUY_BUTTON_SELECTOR = "//div[@id='detail-buying-btns']/button[2]"

def get_random_ua():
    if HAS_FAKE_UA:
        try:
            return ua.random
        except:
            pass
    return random.choice(USER_AGENT_LIST if not HAS_FAKE_UA else USER_AGENT_LIST) # Fallback

def setup_csv(base_path, date_str):
    output_dir = os.path.join(base_path, date_str)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    file_path = os.path.join(output_dir, f"1-fpt-{date_str}.csv")
    img_dir = os.path.join(output_dir, 'img_fpt')
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

async def wait_for_overlay(page):
    """
    Aggressively handles overlays that block clicks.
    """
    try:
        # Common overlay classes (Backdrop, Modal)
        overlays = [
            ".bg-black-opacity-70",
            "div[class*='Backdrop_backdrop']"
        ]
        for sel in overlays:
            loc = page.locator(sel)
            if await loc.count() > 0 and await loc.is_visible():
                await loc.wait_for(state="hidden", timeout=5000)
    except Exception:
        pass

async def handle_popup(page):
    try:
        # "Để sau" button (Later)
        # Use a more generic selector to catch variations
        de_sau_btn = page.locator("button").filter(has_text="Để sau")
        if await de_sau_btn.count() > 0:
             if await de_sau_btn.is_visible():
                # use force=True to bypass some overlays if possible
                await de_sau_btn.click(force=True, timeout=3000)
                await page.wait_for_timeout(500)
    except Exception:
        pass

async def click_and_get_text(page, container_selector, button_selector):
    try:
        btn = page.locator(button_selector).first
        if await btn.count() > 0 and await btn.is_visible():
            try:
                # Force click to avoid "intercepts pointer events" errors
                await btn.click(force=True, timeout=3000)
                await page.wait_for_timeout(500) 
            except Exception:
                pass
        return await get_text_safe(page, container_selector)
    except Exception:
        return ""

async def add_stealth_scripts(page):
    """
    Injects scripts to hide automation properties.
    """
    await page.add_init_script("""
        // Pass the Webdriver Test
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });

        // Mock Chrome runtime
        window.chrome = {
            runtime: {}
        };

        // Mock Plugins/Languages if needed (simplified)
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en', 'vi']
        });
        
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
        });
    """)

async def process_url(semaphore, browser, url, csv_path, csv_lock):
    async with semaphore:
        # Rotate User Agent
        current_ua = get_random_ua()
        
        # Randomize context creation slightly
        page = await browser.new_page(
            user_agent=current_ua,
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1,
            locale="vi-VN",
            timezone_id="Asia/Ho_Chi_Minh"
        )
        
        await add_stealth_scripts(page)

        try:
            print(f"Processing: {url}")
            # SINGLE goto with reduced timeout check
            try:
                await page.goto(url, timeout=45000, wait_until="domcontentloaded")
            except Exception as e:
                print(f"  Timeout loading {url}, retrying once...")
                await page.goto(url, timeout=45000, wait_until="domcontentloaded")

            if USE_SMART_WAIT:
                try:
                    await page.wait_for_selector(PRODUCT_NAME_SELECTOR, timeout=5000)
                except: pass
            
            # Initial popup check
            await handle_popup(page)
            await wait_for_overlay(page)

            await process_storage_options(page, url, csv_path, csv_lock)

        except Exception as e:
            print(f"Error processing {url}: {e}")
        finally:
            try:
                await page.close()
            except: pass

async def process_storage_options(page, url, csv_path, csv_lock):
    storage_container_xpath = "(//div[contains(@class, 'flex flex-wrap gap-2')])[1]"
    
    # CASE 1: Storage Options are Links (<a>)
    storage_links = page.locator(f"{storage_container_xpath}//a")
    link_count = await storage_links.count()

    if link_count > 0:
        print(f"  Found {link_count} storage links. Iterating...")
        hrefs = []
        for i in range(link_count):
            href = await storage_links.nth(i).get_attribute("href")
            if href:
                if not href.startswith("http"):
                    href = "https://fptshop.com.vn" + href
                hrefs.append(href)
        
        seen_urls = set()
        for link in hrefs:
            if link in seen_urls: continue
            seen_urls.add(link)
            
            # Navigate if different
            if link != page.url:
                 try:
                    await page.goto(link, timeout=45000, wait_until="domcontentloaded")
                    await page.wait_for_timeout(1000) 
                    await handle_popup(page)
                 except: continue
            
            await process_color_options(page, link, csv_path, csv_lock)
    else:
        # CASE 2: Storage Options are Buttons
        storage_btns_xpath = f"{storage_container_xpath}/div//button"
        storage_btns = page.locator(storage_btns_xpath)
        count = await storage_btns.count()
        
        if count == 0:
            # Case 3: No storage options (only 1 version)
            await process_color_options(page, url, csv_path, csv_lock)
        else:
            # Iterate buttons
            for i in range(count):
                storage_btns = page.locator(storage_btns_xpath) # Re-query to avoid stale element
                btn = storage_btns.nth(i)
                
                await wait_for_overlay(page)
                await handle_popup(page)
                
                if await btn.is_visible():
                    try:
                        # Force click
                        await btn.click(force=True, timeout=3000)
                        await page.wait_for_timeout(1000)
                        await handle_popup(page)
                        
                        txt = await btn.text_content()
                        name = txt.strip()
                        
                        is_storage = "GB" in name or "TB" in name
                        potential_color = None if is_storage else name
                        
                        await process_color_options(page, url, csv_path, csv_lock, parent_color=potential_color)
                        
                    except Exception as e:
                        print(f"  Error clicking storage {i}: {e}")

async def process_color_options(page, url, csv_path, csv_lock, parent_color=None):
    color_container_xpath = "(//div[contains(@class, 'flex flex-wrap gap-2')])[2]"
    color_btns_xpath = f"{color_container_xpath}/div//button"
    
    color_btns = page.locator(color_btns_xpath)
    count = await color_btns.count()
    
    if count > 0:
        for i in range(count):
            color_btns = page.locator(color_btns_xpath)
            btn = color_btns.nth(i)
            
            await wait_for_overlay(page)
            await handle_popup(page)
            
            if await btn.is_visible():
                txt = await btn.text_content()
                color_name = txt.strip()
                try:
                    # Force Click
                    await btn.click(force=True, timeout=3000)
                    
                    # Short random delay for "human" effect
                    await page.wait_for_timeout(random.randint(500, 1000)) 
                    await handle_popup(page)
                    
                    take_screenshot = True
                    if SCREENSHOT_STRATEGY == "FIRST_ONLY" and i > 0:
                        take_screenshot = False
                    elif SCREENSHOT_STRATEGY == "NONE":
                        take_screenshot = False

                    await scrape_product_data(page, url, csv_path, csv_lock, forced_color=color_name, do_screenshot=take_screenshot)
                except Exception as e:
                    print(f"  Error clicking color {i}: {e}")
    else:
        await scrape_product_data(page, url, csv_path, csv_lock, forced_color=parent_color)

async def scrape_product_data(page, url, csv_path, csv_lock, forced_color=None, do_screenshot=True):
    local_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    now_utc = datetime.now(pytz.utc)
    date_str = now_utc.astimezone(local_tz).strftime('%Y-%m-%d')

    # Data Extraction
    # Data Extraction
    product_name = ""
    try:
        # 1. Primary Selector (with waiting)
        try:
            await page.wait_for_selector(PRODUCT_NAME_SELECTOR, timeout=5000)
        except: pass
        
        product_name = await get_text_safe(page, PRODUCT_NAME_SELECTOR)

        # 2. Fallback: Generic H1
        if not product_name:
             h1_gen = page.locator("h1").first
             if await h1_gen.count() > 0:
                 product_name = await h1_gen.inner_text()
        
        # 3. Fallback: Meta Title
        if not product_name:
             meta_title = page.locator('meta[property="og:title"]').first
             if await meta_title.count() > 0:
                 product_name = await meta_title.get_attribute("content")
        
        # 4. Fallback: .st-name class
        if not product_name:
             st_name = page.locator(".st-name").first
             if await st_name.count() > 0:
                 product_name = await st_name.inner_text()

        # 5. Fallback: Document Title
        if not product_name:
             product_name = await page.title()
             # Clean common suffixes
             if product_name:
                product_name = product_name.split('|')[0].split('-')[0].strip()

    except Exception as e:
        print(f"Product naming error: {e}")
        product_name = "Unknown"

    if not product_name:
        product_name = "Unknown"
    
    # Cleanup Name
    product_name = product_name.strip().replace("Mini", "mini").replace("Wi-Fi", "WiFi")
    for item in ["Tai nghe ", "Thiết bị định vị thông minh ", "Bộ chuyển đổi "]:
        product_name = product_name.replace(item, "")

    # Stock
    ton_kho = "No"
    try:
        # Check buy button text
        buy_btn = page.locator(BUY_BUTTON_SELECTOR).first
        if await buy_btn.is_visible():
            btxt = await buy_btn.inner_text()
            if "mua" in btxt.lower():
                ton_kho = "Yes"
    except: pass

    # Prices
    gia_khuyen_mai_raw = await get_text_safe(page, PRICE_MAIN_SELECTOR)
    gia_niem_yet_raw = await get_text_safe(page, PRICE_SUB_SELECTOR)
    if not gia_niem_yet_raw and gia_khuyen_mai_raw:
        gia_niem_yet_raw = gia_khuyen_mai_raw

    def clean_price(p):
        if not p: return 0
        return p.replace("đ", "").replace("₫", "").replace(".", "").strip()

    gia_khuyen_mai = clean_price(gia_khuyen_mai_raw)
    gia_niem_yet = clean_price(gia_niem_yet_raw)

    # Color
    color = forced_color if forced_color else "Unknown"
    
    # Promos
    khuyen_mai = await get_text_safe(page, PROMO_SELECTOR)
    khuyen_mai = khuyen_mai.replace("Xem chi tiết", "\n").strip()

    other_promo = await click_and_get_text(page, OTHER_PROMO_SELECTOR, OTHER_PROMO_BTN_SELECTOR)
    other_promo = other_promo.replace("Xem chi tiết", "\n").replace("Thu gọn", "").strip()

    thanh_toan = await click_and_get_text(page, THANH_TOAN_SELECTOR, THANH_TOAN_BTN_SELECTOR)
    thanh_toan = thanh_toan.replace("Xem chi tiết", "\n").replace("Thu gọn", "").strip()

    # Screenshot
    screenshot_name = ""
    if do_screenshot and SCREENSHOT_STRATEGY != "NONE":
        try:
            img_dir = os.path.join(os.path.dirname(csv_path), 'img_fpt')
            safe_product_name = re.sub(r'[^\w\-\.]', '_', product_name).strip('. ')
            timestamp_str = datetime.now(local_tz).strftime("%Y-%m-%d_%H-%M-%S")
            
            if len(safe_product_name) > 50: safe_product_name = safe_product_name[:50]
            
            filename = f"{safe_product_name}_{color}_{timestamp_str}.png"
            full_path = os.path.join(img_dir, filename)
            
            # Optimized Screenshot
            await page.screenshot(path=full_path, full_page=True, timeout=5000)
            screenshot_name = filename
        except Exception:
            screenshot_name = "Failed/Skipped"
    else:
        screenshot_name = "Skipped"

    # Save
    data = {
        "Product_Name": product_name,
        "Color": color,
        "Ton_Kho": ton_kho,
        "Gia_Niem_Yet": gia_niem_yet,
        "Gia_Khuyen_Mai": gia_khuyen_mai,
        "Date": date_str,
        "Khuyen_Mai": khuyen_mai,
        "Thanh_Toan": thanh_toan,
        "Other_promotion": other_promo,
        "Link": url,
        "screenshot_name": screenshot_name
    }
    
    await write_to_csv(csv_path, data, csv_lock)
    print(f"Saved: {product_name} - {color}")

async def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.join(current_dir, '../content')
    local_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    date_str = datetime.now(local_tz).strftime('%Y-%m-%d')
    csv_path = setup_csv(base_path, date_str)
    csv_lock = asyncio.Lock()
    
    urls = total_links['fpt_urls']
    print(f"Found {len(urls)} URLs to process.")
    
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TABS)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=HEADLESS,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox"
            ]
        )
        
        random.shuffle(urls)

        tasks = [process_url(semaphore, browser, url, csv_path, csv_lock) for url in urls]
        await asyncio.gather(*tasks)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
