import asyncio
import csv
import os
import random
import re
from datetime import datetime
import pytz
from playwright.async_api import async_playwright

# Configuration
# Since this is a new channel, we'll assign it ID 5
OUTPUT_DIR = "content"
DDV_URLS = [
    "https://didongviet.vn/dien-thoai/iphone-17-pro-max-256gb.html"
]

# Stealth / Anti-bot constants
MAX_CONCURRENT_TABS = 4 # Conservative
HEADLESS = False # DDV specific: Set false initially to verify visual rendering if needed, but script default usually True
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
            "Product_Name", "Color", "Ton_Kho", "Stock_Count", "Gia_Niem_Yet", "Gia_Khuyen_Mai",
             "Date", "Khuyen_Mai", "Thanh_Toan", "Other_promotion", "Link", "screenshot_name"
        ], delimiter=";")
        writer.writeheader()
    return file_path

async def write_to_csv(file_path, data, lock):
    async with lock:
        with open(file_path, "a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=[
                "Product_Name", "Color", "Ton_Kho", "Stock_Count", "Gia_Niem_Yet", "Gia_Khuyen_Mai",
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

async def wait_for_overlay(page):
    try:
        # Generic overlay closer
        close_btns = page.locator("button[aria-label='Close'], .close-popup, .popup-close")
        if await close_btns.count() > 0 and await close_btns.first.is_visible():
            await close_btns.first.click()
    except: pass

async def scrape_product(page, url, csv_path, csv_lock, forced_color="Unknown", screenshot=False):
    local_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    date_str = datetime.now(local_tz).strftime('%Y-%m-%d')

    # 1. Product Name
    product_name = await get_text_safe(page, "h1")
    if not product_name: product_name = "Unknown"
    
    # 2. Price (User Selectors)
    gia_khuyen_mai = 0
    gia_niem_yet = 0
    
    try:
        # Promo Price: //div[@class='flex flex-row items-end gap-4']/div
        gkm_str = await get_text_safe(page, "//div[@class='flex flex-row items-end gap-4']/div")
        if gkm_str:
            gia_khuyen_mai = int(re.sub(r'[^\d]', '', gkm_str)) if re.search(r'\d', gkm_str) else 0

        # Listed Price: //div[@class='flex flex-row items-end gap-4']/span/p[@class=' line-through']
        # Note: The 'line-through' in p class usually has a space in user string: ' line-through'
        gny_str = await get_text_safe(page, "//div[@class='flex flex-row items-end gap-4']/span/p[contains(@class, 'line-through')]")
        if gny_str:
            gia_niem_yet = int(re.sub(r'[^\d]', '', gny_str)) if re.search(r'\d', gny_str) else 0
            
        if gia_niem_yet == 0 and gia_khuyen_mai > 0:
            gia_niem_yet = gia_khuyen_mai
            
    except Exception as e:
        print(f"Price Error: {e}")

    # 3. Stock
    ton_kho = "Yes"
    if await page.locator("text=Hết hàng").count() > 0 or await page.locator("text=Tạm hết hàng").count() > 0:
        ton_kho = "No"

    # Stock Count (Users request: //div[@class='py-2']/p/span)
    stock_count = "0"
    try:
        sc_loc = page.locator("//div[@class='py-2']/p/span").first
        if await sc_loc.count() > 0:
             stock_count = await sc_loc.inner_text()
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
                    # If it toggles visibility, we might need to check state.
                    # Assuming clicking ensures it's shown or expands it.
                    if await dropdowns.nth(i).is_visible():
                        await dropdowns.nth(i).click(force=True)
                        await page.wait_for_timeout(200)
                except: pass

        # Extract Khuyen Mai: //div[@class='border rounded-lg overflow-hidden w-full']
        km_loc = page.locator("//div[@class='border rounded-lg overflow-hidden w-full']")
        if await km_loc.count() > 0:
            khuyen_mai = await km_loc.first.inner_text() 
            # Clean up newlines for CSV
            khuyen_mai = khuyen_mai.replace("\n", " | ").strip()

        # Extract Thanh Toan: //div[@class='flex w-full flex-col items-start justify-start bg-white p-2']
        tt_loc = page.locator("//div[@class='flex w-full flex-col items-start justify-start bg-white p-2']")
        if await tt_loc.count() > 0:
            thanh_toan = await tt_loc.first.inner_text()
            thanh_toan = thanh_toan.replace("\n", " | ").strip()

    except Exception as e: 
        print(f"Promo Error: {e}")
        pass

    # Screenshot
    screenshot_name = ""
    if screenshot:
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
        "Stock_Count": stock_count,
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

async def process_url(page, url, csv_path, csv_lock):
    print(f"Processing: {url}")
    try:
        await page.goto(url, timeout=60000, wait_until="domcontentloaded")
        await wait_for_overlay(page)
        
        # STORAGE Selection
        # Based on debug: div with class 'item' containing GB/TB
        # Broad selector for "Option Items":  item-center py-2 px-1
        # Let's find containers that have these items
        
        # 1. Identify Storage options
        # We look for typical storage strings
        storages_found = []
        for st_txt in ["128GB", "256GB", "512GB", "1TB", "2TB"]:
            # Find element containing this text that looks like a button
            btn = page.locator(f"//div[contains(@class, 'cursor-pointer') or contains(@class, 'item-center')]").filter(has_text=st_txt).first
            if await btn.count() > 0:
                storages_found.append((st_txt, btn))
        
        if not storages_found:
            # Just process directly if no storage options
             await process_colors(page, url, csv_path, csv_lock)
        else:
            # Iterate storage
            for st_name, st_btn in storages_found:
                try:
                    # Click storage
                    if await st_btn.is_visible():
                        await st_btn.click(force=True)
                        await page.wait_for_timeout(1000)
                        # Now process colors for this storage
                        await process_colors(page, url, csv_path, csv_lock)
                except Exception as e:
                    print(f"Error selecting storage {st_name}: {e}")

    except Exception as e:
        print(f"Error processing URL {url}: {e}")

async def process_colors(page, url, csv_path, csv_lock):
    # Identify Color Options
    # We suspect they share classes with storage or are nearby
    # Strategy: Find all "clickable items" in the "Color" container.
    # How to find Color container? Look for "Màu sắc" or assume it's the OTHER set of buttons.
    # Let's try to find buttons that do NOT contain GB/TB.
    
    # Get all option-like buttons
    # Using the generic class seen in debug: 'item-center' or 'border-border'
    # Refined selector based on debug:
    # "item-center py-2 px-1 h-full border-1 item relative flex flex-col justify-center rounded border-border cursor-pointer"
    
    candidates = page.locator("//div[contains(@class, 'cursor-pointer')][contains(@class, 'rounded')]")
    count = await candidates.count()
    
    color_buttons = []
    
    for i in range(count):
        btn = candidates.nth(i)
        txt = await btn.inner_text()
        
        # Filter out Storage
        if "GB" in txt or "TB" in txt:
            continue
            
        # Filter out CTAs
        upper_txt = txt.upper()
        if "MUA" in upper_txt or "TRẢ GÓP" in upper_txt or "THÊM VÀO" in upper_txt:
            continue

        # Filter out empty or irrelevant
        if not txt.strip(): 
            continue # Might be just color circle? If DDV uses text, we stick to text.
            
        # Dedupe based on text to avoid re-clicking same visual element
        color_buttons.append((txt.strip(), btn))

    # Remove duplicates
    unique_colors = []
    seen = set()
    for txt, btn in color_buttons:
        if txt not in seen:
            unique_colors.append((txt, btn))
            seen.add(txt)

    if not unique_colors:
        await scrape_product(page, url, csv_path, csv_lock, forced_color="Default", screenshot=True)
    else:
        for col_name, btn in unique_colors:
            try:
                await btn.click(force=True)
                await page.wait_for_timeout(1000) # Wait for price update
                await scrape_product(page, url, csv_path, csv_lock, forced_color=col_name, screenshot=True)
            except Exception as e:
                print(f"Error scraping color {col_name}: {e}")

async def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.join(current_dir, '../content')
    
    local_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    date_str = datetime.now(local_tz).strftime('%Y-%m-%d')
    csv_path = setup_csv(base_path, date_str)
    csv_lock = asyncio.Lock()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True) # Switch to True for prod
        context = await browser.new_context(
            user_agent=random.choice(USER_AGENT_LIST),
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()
        
        # Stealth
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        for url in DDV_URLS:
            await process_url(page, url, csv_path, csv_lock)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
