import asyncio
import csv
import os
import sys
import re
from datetime import datetime
import pytz
from playwright.async_api import async_playwright

# Add the current directory to sys.path to import sites
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
from utils import sites

# --- Configuration ---
MAX_CONCURRENT_TABS = int(os.environ.get("MAX_CONCURRENT_TABS", 8)) # Optimized for M3
TAKE_SCREENSHOT = os.environ.get("TAKE_SCREENSHOT", "False").lower() == "true"
BLOCK_IMAGES = os.environ.get("BLOCK_IMAGES", "True").lower() == "true"
HEADLESS = True
# MW blocks automation heavily, use standard headers
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

# --- Selectors ---
PRODUCT_NAME_SELECTOR = "h1"
PROMO_SELECTOR = ".promotions, .block__promo"
# MW Colors/Storage are often in 'box03' class
STORAGE_CONTAINER_SELECTOR = ".box03:not(.color)" 
COLOR_CONTAINER_SELECTOR = ".box03.color"

# --- Helper Functions ---
def setup_csv(base_path, date_str):
    output_dir = os.path.join(base_path, date_str)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, f"2-mw-{date_str}.csv")
    
    # Always create fresh or append? FPT logic overwrites to avoid duplicates in single run
    if os.path.exists(file_path):
        try: os.remove(file_path)
        except: pass

    with open(file_path, "w", newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=[
            "Product_Name", "Color", "Ton_Kho", "Gia_Niem_Yet", "Gia_Khuyen_Mai",
            "Date", "Khuyen_Mai", "Thanh_Toan", "Link", 'screenshot_name'
        ], delimiter=";")
        writer.writeheader()
    return file_path

async def write_to_csv(file_path, data, lock):
    async with lock:
        with open(file_path, "a", newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=[
                "Product_Name", "Color", "Ton_Kho", "Gia_Niem_Yet", "Gia_Khuyen_Mai",
                "Date", "Khuyen_Mai", "Thanh_Toan", "Link", 'screenshot_name'
            ], delimiter=";")
            writer.writerow(data)

async def remove_overlays(page):
    """Aggressively remove MW specific overlays."""
    try:
        await page.evaluate("""
            document.querySelectorAll('.popup-modal, .bg-black, .loading-cover, .loading').forEach(e => e.remove());
        """)
    except: pass

async def get_text_safe(page, selector, timeout=500):
    try:
        if await page.locator(selector).count() > 0:
            return await page.locator(selector).first.inner_text()
    except: pass
    return ""

async def get_product_name(page, url):
    # Try H1
    try:
        name = await page.locator(PRODUCT_NAME_SELECTOR).first.text_content()
        if name: return name.strip()
    except: pass
    
    # Try Title
    try:
        title = await page.title()
        if title: return title.split("|")[0].strip()
    except: pass
    
    return "Error getting name"

async def scrape_product_data(page, url, csv_path, csv_lock, forced_color=None):
    # Get Name
    product_name = await get_product_name(page, url)
    product_name = product_name.replace("Điện thoại ", "").replace("Laptop ", "").replace("Máy tính bảng ", "").strip()

    data = {
        "Product_Name": product_name,
        "Color": forced_color if forced_color else "Unknown",
        "Ton_Kho": "No",
        "Gia_Niem_Yet": "0", 
        "Gia_Khuyen_Mai": "0",
        "Date": datetime.now(pytz.timezone('Asia/Ho_Chi_Minh')).strftime("%Y-%m-%d"),
        "Khuyen_Mai": "",
        "Thanh_Toan": "",
        "Link": url,
        "screenshot_name": "Skipped"
    }

    # Price Logic
    try:
        # MW Price logic
        # Wait for price to be visible and not empty
        try:
             await page.wait_for_selector(".bs_price strong, .price-present, .box-price-present", timeout=3000)
        except: pass

        # Helper to clean price
        def clean_price(p_str):
            if not p_str: return "0"
            # Extract first distinct number chain
            # e.g. "17.990.000\n-10%" -> "17990000"
            # Remove all non-numeric except . and newline for processing
            clean = re.sub(r'[^\d\.\n]', '', p_str) 
            # Split by newline if multiple prices/lines
            parts = clean.split('\n')
            for part in parts:
                num = part.replace('.', '')
                if num.isdigit() and len(num) > 4: # Price > 10000
                    return num
            return "0"

        # 1. Shock Price
        shock_price = await get_text_safe(page, ".bs_price strong, .price-present")
        if shock_price:
            data["Gia_Khuyen_Mai"] = clean_price(shock_price)
        
        # 2. Old Price
        old_price = await get_text_safe(page, ".bs_price em, .price-old, .box-price-old")
        if old_price:
            data["Gia_Niem_Yet"] = clean_price(old_price)
            
        # 3. Fallback
        if data["Gia_Khuyen_Mai"] == "0" or data["Gia_Khuyen_Mai"] == "":
             # Try other selectors
             reg = await get_text_safe(page, ".giamsoc-ol-price, .box-price-present, .center b, .prods-price li span, .box-price")
             if reg: data["Gia_Khuyen_Mai"] = clean_price(reg)
             
        if data["Gia_Khuyen_Mai"] == "0":
             data["Gia_Khuyen_Mai"] = data["Gia_Niem_Yet"]
        
        if data["Gia_Khuyen_Mai"] != "0":
            data["Ton_Kho"] = "Yes"
        else:
            # Force Screenshot for debugging Price=0
            try:
                img_dir = os.path.join(os.path.dirname(csv_path), 'img_mw')
                if not os.path.exists(img_dir): os.makedirs(img_dir)
                filename = f"DEBUG_PRICE0_{product_name}_{datetime.now().strftime('%H%M%S')}.png"
                await page.screenshot(path=os.path.join(img_dir, filename), full_page=True)
                data['screenshot_name'] = filename
            except: pass

    except Exception as e:
        print(f"Price error: {e}")

    # Color Fallback if still unknown
    if data["Color"] == "Unknown":
        # Check if color is in name? e.g. "iPhone 15 Pink"
        pass

    try:
        promo = await get_text_safe(page, PROMO_SELECTOR)
        if promo: data["Khuyen_Mai"] = promo
    except: pass

    # Thanh Toan
    try:
        tt_selector = "//div[@class='block__promo']/following-sibling::div[contains(@class, 'campaign')]"
        tt = await get_text_safe(page, tt_selector)
        if tt: data["Thanh_Toan"] = tt.strip()
    except: pass

    # Write
    await write_to_csv(csv_path, data, csv_lock)
    print(f"Saved: {product_name} - {data['Color']} | Price: {data['Gia_Khuyen_Mai']}")


async def process_color_options(page, url, csv_path, csv_lock):
    """Iterate through colors for the CURRENT storage option."""
    # Find active color container
    # MW usually has .box03.color
    try:
        color_btns = page.locator(".box03.color .item")
        count = await color_btns.count()
        
        if count == 0:
            # Check for SINGLE color (sometimes it's just text or a hidden active item?)
            # Or maybe the structure is different.
            # Look for '.box03.color' text content?
             
            # Fallback: Scrape once, name might contain color
            await scrape_product_data(page, url, csv_path, csv_lock, forced_color="Default/Unknown")
            return

        for i in range(count):
            await remove_overlays(page)
            # Re-locate
            btn = page.locator(".box03.color .item").nth(i)
            if await btn.is_visible():
                color_name = await btn.text_content()
                color_name = color_name.strip()
                
                # Check directly if active?
                is_active = await btn.get_attribute("class")
                if "act" in is_active or "check" in is_active:
                    pass # Already selected
                else:
                    try:
                        await btn.click(force=True, timeout=2000)
                        await page.wait_for_timeout(1000) # Small wait for AJAX
                    except: pass
                
                await scrape_product_data(page, url, csv_path, csv_lock, forced_color=color_name)
    except Exception as e:
        print(f"Color loop error: {e}")
        await scrape_product_data(page, url, csv_path, csv_lock)

async def process_storage_options(page, url, csv_path, csv_lock):
    """Iterate through ALL option containers (Storage, RAM, Version)."""
    # MW Structure: Multiple .box03 containers. One might be Color, others might be Storage/RAM.
    # We iterate all .box03 that are NOT color first?
    # Or better: Iterate ALL .box03. 
    # If it's color -> skip (handled in process_color_options or called explicitly)
    # If it's not color -> Click items -> Check Navigation -> Recurse/Continue?
    
    # Simpler approach: 
    # 1. Find the "Storage/Version" container. 
    #    It's usually the one with "GB/TB" text or just the first non-color box.
    
    # Debug: Search for any container that looks like options
    # Debug: Search for any container that looks like options
    # all_divs = await page.locator("div[class*='group'], div[class*='box03']").all()
    # print(f"DEBUG: Extended Search found {len(all_divs)} items") 


    containers = page.locator(".box03, .group.desk") # Try adding .group.desk
    count = await containers.count()
    print(f"DEBUG: Found {count} containers with .box03 OR .group.desk")
    
    found_storage = False
    
    for i in range(count):
        # Check if this container is Color
        cls = await containers.nth(i).get_attribute("class")
        print(f"DEBUG: Container {i} class: '{cls}'")
        
        if "color" in cls:
            print("  -> Skipping (Color)")
            continue # Handled by process_color_options
            
        # This is a potential Storage/Version container
        btns = containers.nth(i).locator("a.item, div.item") # MW uses <a> or <div>
        btn_count = await btns.count()
        
        if btn_count > 1:
            print(f"Found Option Container {i} with {btn_count} items.")
            found_storage = True
            
            # Iterate buttons in this container
            for j in range(btn_count):
                await remove_overlays(page)
                # Re-locate container and btn
                container = page.locator(".box03").nth(i)
                btn = container.locator("a.item, div.item").nth(j)
                
                name = await btn.text_content()
                name = name.strip()
                
                current_url = page.url
                
                # Check active status to avoid unnecessary clicks?
                # class="item act"
                is_active = await btn.get_attribute("class")
                
                print(f"  Clicking Option: {name}")
                try:
                    await btn.click(force=True)
                    
                     # Check Navigation
                    try:
                        await page.wait_for_timeout(2000)
                        await page.wait_for_load_state("domcontentloaded", timeout=3000)
                    except: pass
                    
                    if page.url != current_url:
                        print(f"    -> Navigated to: {page.url}")
                        await remove_overlays(page)
                        
                    # After clicking storage, process colors
                    await process_color_options(page, url, csv_path, csv_lock)
                    
                    # If navigated, we might need to go back? 
                    # MW logic: Clicking storage loads new page. 
                    # The loop continues? 
                    # If we navigated, the previous DOM elements ("containers") are stale!
                    # We MUST break and restart logic on new page? 
                    # Or simpler: For MW, Storage usually implies different URL.
                    # FPT logic handled this by checking URL change.
                    # If URL changed, we are on a new page. We should scrape that page.
                    # The problem is: How to click the NEXT storage button?
                    # On the new page, the other storage buttons exist.
                    # So we need to re-locate the container on the NEW page.
                    
                    if page.url != current_url:
                        # We are on new page. 
                        # We need to re-locate the container to click the next button?
                        # ACTUALLY, if we loop `range(btn_count)`, we are just using index.
                        # As long as the structure is consistent (Storage container is always at index i),
                        # we can continue the loop!
                        pass
                        
                except Exception as e:
                    print(f"    Error clicking {name}: {e}")
                    
            # If we found a storage container and iterated it, should we stop?
            # Or are there multiple storage containers (RAM + SSD)?
            # MW usually combines them or puts them in separate boxes. 
            # If we iterate ALL, we get combinations.
            # For now, let's assume one main "Version" container breaks the detailed variants.
            return # Processed one container, assumed to be the variant selector.

    if not found_storage:
        # No storage container found, just scrape colors
        await process_color_options(page, url, csv_path, csv_lock)

async def process_url(semaphore, browser, url, csv_path, csv_lock):
    async with semaphore:
        page = await browser.new_page(
            user_agent=USER_AGENT,
            viewport={"width": 1920, "height": 1080},
             extra_http_headers={
                "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
                "sec-ch-ua-platform": '"macOS"',
            }
        )
        
        if BLOCK_IMAGES:
            await page.route("**/*", lambda route: route.abort() 
                if route.request.resource_type in ["image", "media", "font"] 
                else route.continue_())

        try:
            print(f"Processing: {url}")
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await remove_overlays(page)
            
            await process_storage_options(page, url, csv_path, csv_lock)

        except Exception as e:
            print(f"Error processing {url}: {e}")
        finally:
            await page.close()

async def main():
    date_str = datetime.now(pytz.timezone('Asia/Ho_Chi_Minh')).strftime("%Y-%m-%d")
    base_path = os.path.join(current_dir, '../content')
    csv_path = setup_csv(base_path, date_str)
    csv_lock = asyncio.Lock()
    
    initial_urls = sites.total_links['mw_urls']
    if os.environ.get("TEST_MODE") == "False":
        # Macbook Debug URL
        initial_urls = ["https://www.thegioididong.com/laptop/macbook-air-13-inch-m4-16gb-256gb"]
        print("⚠️ TEST MODE ENABLED: Debugging Macbook Storage")
    
    print(f"Found {len(initial_urls)} URLs to process.")
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TABS)
    
    async with async_playwright() as p:
        # Proxy Setup (Same as FPT)
        proxy_server = os.environ.get("PROXY_SERVER", "").strip()
        launch_options = {
            "headless": HEADLESS,
            "args": ["--disable-blink-features=AutomationControlled", "--window-size=1920,1080"],
            "ignore_default_args": ["--enable-automation"]
        }
        if proxy_server:
            # Basic parsing logic derived from previous files
            if "@" not in proxy_server and len(proxy_server.split(':')) == 4:
                 ip, port, user, pw = proxy_server.split(':')
                 proxy_server = f"http://{user}:{pw}@{ip}:{port}"
            if not proxy_server.startswith("http"): proxy_server = f"http://{proxy_server}"
            if os.environ.get("ENABLE_PROXY_MW", "False").lower() == "true":
                launch_options["proxy"] = {"server": proxy_server}

        browser = await p.chromium.launch(**launch_options)
        tasks = [process_url(semaphore, browser, url, csv_path, csv_lock) for url in initial_urls]
        await asyncio.gather(*tasks)
        await browser.close()

if __name__ == "__main__":
    start = datetime.now()
    asyncio.run(main())
    duration = datetime.now() - start
    seconds = duration.total_seconds()
    print(f"Total execution time: {int(seconds // 3600)} hours {int((seconds % 3600) // 60)} minutes {int(seconds % 60)} seconds")
