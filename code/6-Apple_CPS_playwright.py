import asyncio
import csv
import json
import re
import os
import sys
import time
import random
from datetime import datetime
import pytz
from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeoutError

# Add the current directory to sys.path to import sites
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
from utils import sites

# --- Configuration ---
MAX_CONCURRENT_TABS = int(os.environ.get("MAX_CONCURRENT_TABS", 10))
TAKE_SCREENSHOT = os.environ.get("TAKE_SCREENSHOT", "False").lower() == "true"
BLOCK_IMAGES = os.environ.get("BLOCK_IMAGES", "True").lower() == "true"
HEADLESS = True
# Only use first 4 URLs for testing if TEST_MODE is True
TEST_MODE = os.environ.get("TEST_MODE", "False").lower() == "true"
# Enable Gap Filling (recursive discovery of missing variants)
ENABLE_GAP_FILLING = os.environ.get("ENABLE_GAP_FILLING", "False").lower() == "true"

USER_AGENT_LIST = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]

# --- Selectors ---
# Product Name: h1 inside .box-product-name
PRODUCT_NAME_SELECTOR = "div.box-product-name h1" 
# Price Sale: p.sale-price (Updated 2024-12-24)
# Price Sale: p.sale-price or div.sale-price (Updated 2024-12-24)
PRICE_MAIN_SELECTOR = ".sale-price"
# Price Original: del.base-price or p.product__price--through (Updated 2024-12-24)
PRICE_SUB_SELECTOR = "del.base-price"
# Promo: div.box-product-promotion
PROMO_SELECTOR = "div.box-product-promotion"
# Payment Promo: div.box-more-promotion (often inside .box-more-promotion)
PAYMENT_PROMO_SELECTOR = "div.box-more-promotion"
# Color Options: a.button__change-color (or li.button__change-color depending on structure)
COLOR_OPTIONS_SELECTOR = "//ul[contains(@class, 'list-variants')]/li"
# Stock Button: .button-desktop-order or .button-desktop-order-now
STOCK_INDICATOR_SELECTOR = ".button-desktop-order-now, .button-desktop-order"
# Storage Options: a.item-linked
STORAGE_OPTIONS_SELECTOR = "//div[contains(@class, 'list-linked')]/a"

# --- Helper Functions ---
def setup_csv(base_path, date_str):
    output_dir = os.path.join(base_path, date_str)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    file_path = os.path.join(output_dir, f"6-cps-{date_str}.csv")
    
    img_dir = os.path.join(output_dir, 'img_cps')
    if not os.path.exists(img_dir):
        os.makedirs(img_dir, exist_ok=True)

    # Overwrite if exists
    with open(file_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=[
            "Product_Name", "Color", "Ton_Kho", "Gia_Niem_Yet", "Gia_Khuyen_Mai",
             "Date", "Khuyen_Mai", "Thanh_Toan", "Link", "screenshot_name"
        ], delimiter=";")
        writer.writeheader()
    return file_path

async def write_to_csv(file_path, data, lock):
    async with lock:
        with open(file_path, "a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=[
                "Product_Name", "Color", "Ton_Kho", "Gia_Niem_Yet", "Gia_Khuyen_Mai",
                 "Date", "Khuyen_Mai", "Thanh_Toan", "Link", "screenshot_name"
            ], delimiter=";")
            writer.writerow(data)

async def get_text_safe(page, selector, timeout=1000):
    try:
        loc = page.locator(selector).first
        if await loc.count() > 0:
            return await loc.inner_text()
    except: pass
    return ""

class CPSInteractor:
    def __init__(self, page, url, csv_path, csv_lock):
        self.page = page
        self.url = url
        self.csv_path = csv_path
        self.csv_lock = csv_lock
        self.local_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        self.date_str = datetime.now(self.local_tz).strftime('%Y-%m-%d')

    async def extract_data(self, color_name="Unknown", screenshot=False):
        # 1. Product Name
        product_name = await get_text_safe(self.page, PRODUCT_NAME_SELECTOR)
        if not product_name: 
            product_name = await self.page.title()
        
        # Clean Name
        for item in ["Chính hãng", " I ", " | ", " VN/A", " Apple Việt Nam", "Chính Hãng"]:
            product_name = product_name.replace(item, "")
        product_name = product_name.strip()

        # 2. Prices
        gia_khuyen_mai_raw = await get_text_safe(self.page, PRICE_MAIN_SELECTOR)
        gia_niem_yet_raw = await get_text_safe(self.page, PRICE_SUB_SELECTOR)
        if not gia_niem_yet_raw:
             gia_niem_yet_raw = await get_text_safe(self.page, ".product__price--through")
        
        def clean_price(p):
            if not p: return "0"
            return str(p).replace("đ", "").replace("₫", "").replace(".", "").replace(",", "").strip()

        gia_khuyen_mai = clean_price(gia_khuyen_mai_raw)
        gia_niem_yet = clean_price(gia_niem_yet_raw)
        
        if gia_niem_yet == "0" and gia_khuyen_mai != "0":
            gia_niem_yet = gia_khuyen_mai

        # 3. Stock
        ton_kho = "No"
        try:
            # Check Buy Button Text
            # Priority 1: Sticky Button (.button-desktop-order)
            btn_loc = self.page.locator(STOCK_INDICATOR_SELECTOR).first
            if await btn_loc.count() > 0 and await btn_loc.is_visible():
                 btn_text = await btn_loc.inner_text()
                 if "MUA NGAY" in btn_text.upper():
                     ton_kho = "Yes"
            else:
                 # Priority 2: Inline CTA Button (class "btn-cta")
                 # Must check text because "Tra Gop" also uses btn-cta
                 cta_btns = self.page.locator("//button[contains(@class, 'btn-cta')]")
                 count = await cta_btns.count()
                 for i in range(count):
                     if await cta_btns.nth(i).is_visible():
                         txt = await cta_btns.nth(i).inner_text()
                         if "MUA NGAY" in txt.strip().upper():
                             ton_kho = "Yes"
                             break
        except: pass

        # 4. Promotions
        khuyen_mai = ""
        try:
            km_text = await get_text_safe(self.page, PROMO_SELECTOR)
            if km_text:
                khuyen_mai = re.sub(r'\n+', '\n', km_text.strip())
        except: pass

        # 5. Payment Promo
        thanh_toan = ""
        try:
             tt_text = await get_text_safe(self.page, PAYMENT_PROMO_SELECTOR)
             if tt_text:
                 thanh_toan = re.sub(r'\n+', '\n', tt_text.strip())
        except: pass

        # 6. Screenshot
        screenshot_name = ""
        if (TAKE_SCREENSHOT or gia_khuyen_mai == "0") and screenshot:
            try:
                img_dir = os.path.join(os.path.dirname(self.csv_path), 'img_cps')
                safe_name = re.sub(r'[^\w\-\.]', '_', product_name)[:30]
                safe_color = re.sub(r'[^\w\-\.]', '_', color_name)[:10]
                fname = f"{safe_name}_{safe_color}_{datetime.now().strftime('%H%M%S')}.png"
                await self.page.screenshot(path=os.path.join(img_dir, fname), full_page=True)
                screenshot_name = fname
            except: pass
            
        # 7. Save
        data = {
            "Product_Name": product_name,
            "Color": color_name.strip(),
            "Ton_Kho": ton_kho,
            "Gia_Niem_Yet": gia_niem_yet,
            "Gia_Khuyen_Mai": gia_khuyen_mai,
            "Date": self.date_str,
            "Khuyen_Mai": khuyen_mai,
            "Thanh_Toan": thanh_toan,
            "Link": self.page.url,
            "screenshot_name": screenshot_name
        }
        await write_to_csv(self.csv_path, data, self.csv_lock)
        print(f"Saved: {product_name} - {color_name} | Price: {gia_khuyen_mai}")

    async def process_colors(self):
        # 1. Find all color options
        # Selector: .button__change-color
        try:
            # Wait for colors to load (robustness fix)
            try:
                 await self.page.wait_for_selector(COLOR_OPTIONS_SELECTOR, timeout=3000)
            except: pass

            candidates = self.page.locator(COLOR_OPTIONS_SELECTOR)
            count = await candidates.count()
            
            if count == 0:
                print("No color options found, scraping current page.")
                await self.extract_data("Default")
                return

            print(f"Found {count} color options.")
            
            for i in range(count):
                try:
                    # Relocate to handle stale elements
                    btn = self.page.locator(COLOR_OPTIONS_SELECTOR).nth(i)
                    
                    if not await btn.is_visible(): continue
                    
                    # Extract Color Name
                    # Structure: li > a > div > strong
                    color_name = ""
                    strong = btn.locator("strong")
                    if await strong.count() > 0:
                        color_name = await strong.first.inner_text()
                    else:
                        # Fallback: Check title on the <a> tag inside <li>
                        a_tag = btn.locator("a")
                        if await a_tag.count() > 0:
                            color_name = await a_tag.get_attribute("title")
                        else:
                            color_name = await btn.get_attribute("title")
                    
                    if not color_name: color_name = f"Color_{i}"
                    
                    # Click to switch
                    # Handle active state check? Not strictly necessary if we click everything.
                    # CPS updates URL query param ?product_id=...
                    current_url = self.page.url
                    
                    await btn.click(force=True)
                    
                    # Wait for SPA update
                    # 1. URL change?
                    # 2. Or Price element update?
                    await self.page.wait_for_timeout(500) # Reduced from 1500 for speed 
                    
                    await self.extract_data(color_name=color_name, screenshot=True)
                    
                except Exception as e:
                    print(f"Error processing color {i}: {e}")
                    
        except Exception as e:
            print(f"Error in process_colors: {e}")

async def process_url(semaphore, browser, url, csv_path, csv_lock):
    async with semaphore:
        page = await browser.new_page(
            user_agent=random.choice(USER_AGENT_LIST),
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1,
        )
        
        if BLOCK_IMAGES:
            await page.route("**/*", lambda route: route.abort() 
                if route.request.resource_type in ["image", "media", "font"] 
                else route.continue_())

        print(f"Processing: {url}")
        try:
            try:
                t0_load = time.time()
                await page.goto(url, timeout=60000, wait_until="domcontentloaded")
                print(f"  -> Page load took {time.time()-t0_load:.2f}s")
            except:
                print(f"Retry loading {url}")
                await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            
            # Use Interactor directly on the provided URL
            t0_proc = time.time()
            interactor = CPSInteractor(page, url, csv_path, csv_lock)
            await interactor.process_colors()
            print(f"  -> Main Processing took {time.time()-t0_proc:.2f}s")

            # --- Storage Variant Discovery (Gap Filling) ---
            # Only process variants that are NOT in the main input list.
            if ENABLE_GAP_FILLING:
                try:
                    # Use user provided selector
                    links = page.locator(STORAGE_OPTIONS_SELECTOR)
                    count = await links.count()
                    
                    discovered_urls = []
                    for i in range(count):
                        try:
                            href = await links.nth(i).get_attribute("href")
                            if href:
                                full = href if href.startswith("http") else "https://cellphones.com.vn" + href if href.startswith("/") else "https://cellphones.com.vn/" + href
                                full = full.split('?')[0] # Remove query params
                                if ".html" in full:
                                    discovered_urls.append(full)
                        except: pass
                    
                    # Filter: Process ONLY if not in main list and not current
                    cps_set = set(sites.total_links['cps_urls'])
                    
                    for s_url in set(discovered_urls):
                        if s_url == url.split('?')[0]: continue
                        if s_url in cps_set:
                            # present in main list, skip to avoid double work
                            continue
                            
                        print(f"  Gap Filling: Found new variant {s_url}")
                        # Process this new variant
                        try:
                            if s_url != page.url.split('?')[0]:
                                t_nav = time.time()
                                await page.goto(s_url, timeout=60000, wait_until="domcontentloaded")
                                print(f"    -> Gap Nav took {time.time()-t_nav:.2f}s")
                            
                            sub_interactor = CPSInteractor(page, s_url, csv_path, csv_lock)
                            await sub_interactor.process_colors()
                        except Exception as e:
                            print(f"    Error filling gap {s_url}: {e}")

                except Exception as e:
                    print(f"  Storage discovery error: {e}")

        except Exception as e:
            print(f"Error processing {url}: {e}")
        finally:
            await page.close()

async def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.join(current_dir, '../content')
    
    local_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    date_str = datetime.now(local_tz).strftime('%Y-%m-%d')
    csv_path = setup_csv(base_path, date_str)
    csv_lock = asyncio.Lock()
    
    urls_to_process = sites.total_links['cps_urls']
    specific_url = os.environ.get("SPECIFIC_URL")
    if specific_url:
        print(f"⚠️ PROCESSING SPECIFIC URL: {specific_url}")
        urls_to_process = [specific_url]
    elif TEST_MODE:
        print("⚠️ TEST MODE: Processing first 6 URLs only.")
        urls_to_process = urls_to_process[:6]

    print(f"Processing {len(urls_to_process)} URLs with {MAX_CONCURRENT_TABS} concurrent tabs.")
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TABS)

    async with async_playwright() as p:
        # Proxy Logic
        proxy_server = os.environ.get("PROXY_SERVER")
        launch_options = {
            "headless": HEADLESS,
            "args": [
                "--disable-blink-features=AutomationControlled", 
                "--no-sandbox", 
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--window-size=1920,1080"
            ]
        }
        
        if proxy_server and os.environ.get("ENABLE_PROXY_CPS", "False").lower() == "true":
             print(f"🌐 Using Proxy (CPS): {proxy_server}")
             launch_options["proxy"] = {"server": proxy_server}

        browser = await p.chromium.launch(**launch_options)
        
        tasks = [process_url(semaphore, browser, url, csv_path, csv_lock) for url in urls_to_process]
        await asyncio.gather(*tasks)
        await browser.close()

if __name__ == "__main__":
    start_time = datetime.now()
    asyncio.run(main())
    duration = datetime.now() - start_time
    print(f"Total execution time: {duration}")

