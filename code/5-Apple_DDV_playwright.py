import asyncio
import csv
import os
import random
import re
from datetime import datetime
import pytz
from playwright.async_api import async_playwright

import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
from utils.sites import total_links

# Configuration
OUTPUT_DIR = "content"
DDV_URLS = total_links['ddv_urls']

# Default: Take screenshots = False, Block Images = True
# For GitHub Actions/Proxies: These defaults are now optimized for speed/cost.
TAKE_SCREENSHOT = os.environ.get("TAKE_SCREENSHOT", "False").lower() == "true"
BLOCK_IMAGES = os.environ.get("BLOCK_IMAGES", "True").lower() == "true"

# Stealth / Anti-bot constants
MAX_CONCURRENT_TABS = int(os.environ.get("MAX_CONCURRENT_TABS", 10))
HEADLESS = True
# User asked based on experience of others which were Headless=True. I'll stick to True but add User Agent.

USER_AGENT_LIST = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

def setup_csv(base_path, date_str):
    output_dir = os.path.join(base_path, date_str)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    file_path = os.path.join(output_dir, f"5-ddv-{date_str}.csv")
    img_dir = os.path.join(output_dir, 'img_ddv')
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

async def get_text_safe(page, selector, timeout=2000):
    try:
        loc = page.locator(selector).first
        if await loc.count() > 0 and await loc.is_visible(timeout=timeout):
            return await loc.inner_text()
    except: pass
    return ""

# Stealth
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

async def wait_for_overlay(page):
    try:
        # Generic overlay closer
        close_btns = page.locator("button[aria-label='Close'], .close-popup, .popup-close")
        if await close_btns.count() > 0 and await close_btns.first.is_visible():
            await close_btns.first.click()
    except: pass

async def scrape_product(page, url, csv_path, csv_lock, forced_color="Unknown", current_storage="", screenshot=False):
    local_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    date_str = datetime.now(local_tz).strftime('%Y-%m-%d')

    # 1. Product Name
    product_name = await get_text_safe(page, "h1")
    if not product_name: product_name = "Unknown"
    
    # Check if H1 matches current_storage
    if current_storage and current_storage not in product_name:
        # User reported duplicates because H1 doesn't update (e.g. stays 128GB when 512GB clicked).
        # We must force-update the storage in the name.
        # Regex to find existing GB/TB
        match = re.search(r'(\d+)\s?(GB|TB)', product_name, re.IGNORECASE)
        if match:
             # Replace existing storage (e.g. 128GB) with current_storage
             old_storage = match.group(0)
             product_name = product_name.replace(old_storage, current_storage)
        else:
             # Append if no storage found
             product_name = f"{product_name} {current_storage}"
    
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
            
        # --- Fallback Strategy ---
        if gia_khuyen_mai == 0:
             # Try getting price from the Active Button (Red Shadow)
             # XPath: //button[contains(@class, 'bg-white shadow shadow-red-500/50')]
             # Promo is usually the first <p> or just text inside
             btn_gkm = await get_text_safe(page, "//button[contains(@class, 'bg-white shadow shadow-red-500/50')]/p")
             if btn_gkm:
                 gia_khuyen_mai = int(re.sub(r'[^\d]', '', btn_gkm)) if re.search(r'\d', btn_gkm) else 0
                 
             if gia_niem_yet == 0:
                 # Listed price is often inside a div/p in that same button
                 btn_gny = await get_text_safe(page, "//button[contains(@class, 'bg-white shadow shadow-red-500/50')]//div/p")
                 if btn_gny:
                      gia_niem_yet = int(re.sub(r'[^\d]', '', btn_gny)) if re.search(r'\d', btn_gny) else 0

        if gia_niem_yet == 0 and gia_khuyen_mai > 0:
            gia_niem_yet = gia_khuyen_mai
            
    except Exception as e:
        print(f"Price Error: {e}")

    # 3. Stock
    ton_kho = "No" # Default to No

    # User Request: Check for MUA NGAY to confirm stock
    try:
        # Verified via browser: Mua Ngay is in a <p> inside a <button>, but classes vary.
        # Robust Selector: //button//p that contains "Mua ngay"
        buy_text_loc = page.locator("//button//p").filter(has_text=re.compile("mua ngay", re.IGNORECASE)).first
        if await buy_text_loc.count() > 0 and await buy_text_loc.is_visible():
             ton_kho = "Yes"
    except:
        pass

    # Stock Count (Users request: //div[@class='py-2']/p/span)
    Store_Count = "0"
    try:
        sc_loc = page.locator("//div[@class='py-2']/p/span").first
        if await sc_loc.count() > 0:
             Store_Count = await sc_loc.inner_text()
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
                    # Click to expand if needed. 
                    if await dropdowns.nth(i).is_visible():
                        await dropdowns.nth(i).click(force=True)
                        await page.wait_for_timeout(200)
                except: pass

        # Extract Khuyen Mai: //div[@class='border rounded-lg overflow-hidden w-full']
        km_loc = page.locator("//div[@class='border rounded-lg overflow-hidden w-full']")
        if await km_loc.count() > 0:
            khuyen_mai = await km_loc.first.inner_text() 
            # Clean up newlines for CSV (User requested line-by-line)
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
    if screenshot and TAKE_SCREENSHOT:
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
        # Create fresh page
        page = await browser.new_page(
            user_agent=random.choice(USER_AGENT_LIST),
            viewport={"width": 1920, "height": 1080},
            locale="vi-VN",
            timezone_id="Asia/Ho_Chi_Minh",
            extra_http_headers={
                "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Ch-Ua": '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"macOS"',
            }
        )
        await add_stealth_scripts(page)
        
        # Optimize: Block images to save bandwidth/speed if requested
        if BLOCK_IMAGES:
            await page.route("**/*", lambda route: route.abort() 
                if route.request.resource_type in ["image", "media", "font"] 
                else route.continue_())

        print(f"Processing: {url}")
        try:
            try:
                await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            except:
                 print(f"timeout loading {url}, retrying...")
                 await page.goto(url, timeout=60000, wait_until="domcontentloaded")

            await wait_for_overlay(page)
            
            # --- 1. STORAGE SELECTION ---
            # User Requirement: Click explicit storage links identified by:
            # //a[@href]/div[contains(@class, 'cursor-pointer')][contains(@class, 'rounded')]
            
            storage_candidates = page.locator("//a[@href]/div[contains(@class, 'cursor-pointer')][contains(@class, 'rounded')]")
            count = await storage_candidates.count()
            
            if count == 0:
                # No storage options found? Just process the current page.
                 await process_colors(page, url, csv_path, csv_lock)
            else:
                # Iterate through distinct storage options
                for i in range(count):
                    try:
                        # Re-locate to avoid stale element errors
                        storage_candidates = page.locator("//a[@href]/div[contains(@class, 'cursor-pointer')][contains(@class, 'rounded')]")
                        
                        # Note: The clickable element is technically the <div>, but the href is on the parent <a>.
                        # We click the <div>.
                        btn_div = storage_candidates.nth(i)
                        
                        if await btn_div.is_visible():
                            store_text = await btn_div.inner_text()
                            store_text = store_text.strip()
                            
                            # Click it
                            await btn_div.click(force=True)
                            await page.wait_for_timeout(1000) # Wait for navigation/update
                            
                            # Process colors for this specific storage variant
                            await process_colors(page, url, csv_path, csv_lock, current_storage=store_text)
                    except Exception as e:
                        print(f"Error selecting storage {i}: {e}")
            
        except Exception as e:
            print(f"Error processing URL {url}: {e}")
        finally:
            await page.close()

async def process_colors(page, url, csv_path, csv_lock, current_storage=""):
    # --- 2. COLOR SELECTION ---
    # User Requirement: Click explicit color buttons identified by:
    # //div[contains(@class, 'cursor-pointer')][contains(@class, 'rounded')][not(ancestor::a[@href])][not(ancestor::button)]
    # This specifically EXCLUDES Storage links and Buy Buttons.

    candidates = page.locator("//div[contains(@class, 'cursor-pointer')][contains(@class, 'rounded')][not(ancestor::a[@href])][not(ancestor::button)]")
    count = await candidates.count()
    
    color_buttons = []
    
    for i in range(count):
        btn = candidates.nth(i)
        
        if not await btn.is_visible():
            continue

        txt = await btn.inner_text()
        
        # Safety Filters (Just in case HTML is weird)
        if "GB" in txt or "TB" in txt: continue 
        
        upper_txt = txt.upper()
        if "MUA" in upper_txt or "TRẢ GÓP" in upper_txt or "THÊM VÀO" in upper_txt: continue

        if not txt.strip(): continue 

        # Filter out disabled colors (Grayed out)
        class_attr = await btn.get_attribute("class")
        if class_attr:
             if "opacity-40" in class_attr or "cursor-not-allowed" in class_attr or "pointer-events-none" in class_attr or "bg-gray-200" in class_attr:
                 # print(f"  Skipping disabled color: {txt}")
                 continue

        # Valid color candidate found
        color_buttons.append((txt.strip(), btn))

    # Deduplicate by text (e.g. if multiple visual elements imply same color)
    unique_colors = []
    seen = set()
    for txt, btn in color_buttons:
        if txt not in seen:
            unique_colors.append((txt, btn))
            seen.add(txt)

    if not unique_colors:
        # No colors found? Scrape as Default
        await scrape_product(page, url, csv_path, csv_lock, forced_color="Default", current_storage=current_storage, screenshot=True)
    else:
        # Click each unique color
        for col_name, btn in unique_colors:
            try:
                await btn.click(force=True)
                await page.wait_for_timeout(1000) # Wait for price update
                await scrape_product(page, url, csv_path, csv_lock, forced_color=col_name, current_storage=current_storage, screenshot=True)
            except Exception as e:
                print(f"Error scraping color {col_name}: {e}")

async def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.join(current_dir, '../content')
    
    local_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    date_str = datetime.now(local_tz).strftime('%Y-%m-%d')
    csv_path = setup_csv(base_path, date_str)
    csv_lock = asyncio.Lock()
    
    print(f"Processing {len(DDV_URLS)} URLs with {MAX_CONCURRENT_TABS} concurrent tabs.")
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TABS)

    async with async_playwright() as p:
        # Proxy Configuration
        proxy_server = os.environ.get("PROXY_SERVER")
        launch_options = {
            "headless": HEADLESS,
            "channel": "chrome",
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-accelerated-2d-canvas",
                "--disable-gpu",
                "--window-size=1920,1080"
            ],
            "ignore_default_args": ["--enable-automation"]
        }
        
        if proxy_server and os.environ.get("ENABLE_PROXY_DDV", "False").lower() == "true":
            print(f"🌐 Using Proxy (DDV): {proxy_server}")
            launch_options["proxy"] = {"server": proxy_server}

        browser = await p.chromium.launch(**launch_options)
        
        tasks = [process_url(semaphore, browser, url, csv_path, csv_lock) for url in DDV_URLS]
        await asyncio.gather(*tasks)
            
        await browser.close()

if __name__ == "__main__":
    start_time = datetime.now()
    asyncio.run(main())
    
    duration = datetime.now() - start_time
    seconds = duration.total_seconds()
    print(f"Total execution time: {int(seconds // 3600)} hours {int((seconds % 3600) // 60)} minutes {int(seconds % 60)} seconds")
