import asyncio
import csv
import json
import re
import os
import sys
from datetime import datetime
import pytz
from playwright.async_api import async_playwright, Page, Locator
from utils.sites import total_links

# Constants
MAX_CONCURRENT_TABS = int(os.environ.get("MAX_CONCURRENT_TABS", 3)) # Reduced for stability
TAKE_SCREENSHOT = os.environ.get("TAKE_SCREENSHOT", "False").lower() == "true"
BLOCK_IMAGES = os.environ.get("BLOCK_IMAGES", "True").lower() == "true"
HEADLESS = os.environ.get("HEADLESS", "True").lower() == "true"
TEST_MODE = os.environ.get("TEST_MODE", "False").lower() == "true"

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

# Selectors
PRODUCT_NAME_SELECTOR = "h1"
PRICE_CURRENT_SELECTOR = ".box-price strong" 
PRICE_OLD_SELECTOR = ".box-price span"
# Right side color options: The container following the 'Lựa chọn màu' title
# We look for the h4 or strong containing 'Lựa chọn màu', then its next sibling div, then .item inside it.
# Or just generically .item inside the option container if stable.
# Inspection suggests: //strong[contains(text(),'Lựa chọn màu')]/ancestor::div[contains(@class,'order-product')]//div[contains(@class,'item')]
# Let's try a robust path based on the "Lựa chọn màu" header.
COLOR_WRAPPER_SELECTOR = "//div[contains(@class, 'order-product')]//strong[contains(text(), 'Lựa chọn màu')]/parent::div/following-sibling::div"
COLOR_OPTIONS_SELECTOR = f"{COLOR_WRAPPER_SELECTOR}//div[contains(@class, 'item')]" 

STOCK_INDICATOR_SELECTOR = "a.btnQuickOrder" # Check for class 'disabled'
PROMO_SELECTOR = "#product-promotion-content"
PAYMENT_PROMO_SELECTOR = ".promotion-slide-item"

def setup_csv(base_path, date_str):
    output_dir = os.path.join(base_path, date_str)
    os.makedirs(output_dir, exist_ok=True)
    
    file_path = os.path.join(output_dir, f"4-hoangha-{date_str}.csv")
    
    # Create img_hoangha directory
    img_dir = os.path.join(output_dir, 'img_hoangha')
    os.makedirs(img_dir, exist_ok=True)

    if not os.path.exists(file_path):
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

class HoangHaInteractor:
    def __init__(self, page: Page, url: str, csv_path: str, csv_lock: asyncio.Lock):
        self.page = page
        self.url = url
        self.csv_path = csv_path
        self.csv_lock = csv_lock
        self.local_tz = pytz.timezone('Asia/Ho_Chi_Minh')

    async def get_text_safe(self, selector, timeout=1000):
        try:
            # Try innerText first (visible text)
            if await self.page.locator(selector).count() > 0:
                try:
                    return await self.page.locator(selector).first.inner_text(timeout=timeout)
                except:
                    # Fallback to textContent (hidden text ok)
                    return await self.page.locator(selector).first.text_content(timeout=timeout)
            return ""
        except:
            return ""
            
    async def scrape_variant(self, color_name):
        # 1. Product Name
        product_name = await self.get_text_safe(PRODUCT_NAME_SELECTOR)
        if not product_name:
             # Try fallback selectors
             product_name = await self.get_text_safe(".top-product h1")
        if not product_name:
             product_name = await self.get_text_safe("strong.name") 
        
        if not product_name:
             print(f"  DEBUG: Product name empty for {self.url}. Taking screenshot.")
             try:
                 await self.page.screenshot(path=f"debug_empty_{datetime.now().timestamp()}.png", full_page=True)
             except: pass
        
        if product_name:
            product_name = product_name.strip().split(" - ")[0]

        # 2. Stock (Ton_Kho)
        # Check if "MUA NGAY" button is disabled/missing
        ton_kho = "Yes"
        try:
            # Check both common button types
            btn = self.page.locator("a.btnQuickOrder, a.add-cart, .btn-buy").first
            if await btn.count() > 0:
                is_disabled = await btn.get_attribute("class")
                if is_disabled and "disabled" in is_disabled.lower():
                    ton_kho = "No"
                
                # Check text content (safer than innerText)
                try:
                    text = await btn.text_content()
                    text = text.upper() if text else ""
                    if "HẾT HÀNG" in text or "LIÊN HỆ" in text or "TẠM HẾT" in text:
                        ton_kho = "No"
                except: pass
            else:
                # If button is missing completely, assume OOS or error
                # But for some pages, maybe only "Contact" exists?
                # Defaulting to No if no buy button is safer?
                # Actually, some preview items might not have buy button.
                ton_kho = "No"
        except:
            ton_kho = "No"

        # 3. Prices
        gia_khuyen_mai_raw = await self.get_text_safe(PRICE_CURRENT_SELECTOR)
        gia_niem_yet_raw = await self.get_text_safe(PRICE_OLD_SELECTOR)
        
        if not gia_niem_yet_raw and gia_khuyen_mai_raw:
            gia_niem_yet_raw = gia_khuyen_mai_raw

        def clean_price(p):
            if not p: return 0
            # Remove dots, 'đ', '₫', whitespace
            return re.sub(r'[^\d]', '', str(p))

        gia_khuyen_mai = clean_price(gia_khuyen_mai_raw)
        gia_niem_yet = clean_price(gia_niem_yet_raw)
        
        # 4. Promo (Khuyen_Mai)
        try:
            # Get text from promo content box
            # Correct structure: #product-promotion-content > .promotion-item
            promo_box = self.page.locator(PROMO_SELECTOR)
            if await promo_box.count() > 0:
                # Iterate items for cleaner text
                items = promo_box.locator(".promotion-item")
                count = await items.count()
                texts = []
                if count > 0:
                    for i in range(count):
                        text = await items.nth(i).inner_text()
                        if text:
                             texts.append(text.strip())
                    khuyen_mai = "\n".join(texts)
                else:
                     # Fallback to full text if items not found
                     text = await promo_box.inner_text()
                     if text:
                         khuyen_mai = re.sub(r'\n+', '\n', text.strip())
                
                # Sanitize quotes
                khuyen_mai = khuyen_mai.replace('"', "'")
        except: pass
        
        # 5. Payment Promo (Thanh Toan)
        thanh_toan = ""
        try:
            payment_promos = []
            payment_elements = self.page.locator(PAYMENT_PROMO_SELECTOR)
            count = await payment_elements.count()
            for i in range(count):
                # Data often in data-promotion attribute as JSON
                data_attr = await payment_elements.nth(i).get_attribute("data-promotion")
                if data_attr:
                    try:
                        import html
                        decoded = html.unescape(data_attr) # Handle &quot;
                        promos_list = json.loads(decoded)
                        if isinstance(promos_list, list):
                            for p in promos_list:
                                if "Title" in p:
                                     # Sanitize quotes
                                    clean_title = p["Title"].strip().replace('"', "'")
                                    payment_promos.append(clean_title)
                    except: pass
            
            if payment_promos:
                thanh_toan = "\n".join(payment_promos)
        except: pass

        # Screenshot if configured
        screenshot_name = ""
        if TAKE_SCREENSHOT:
            try:
                img_dir = os.path.join(os.path.dirname(self.csv_path), 'img_hoangha')
                safe_name = re.sub(r'[^\w\-\.]', '_', product_name)
                safe_color = re.sub(r'[^\w\-\.]', '_', color_name)
                ts = datetime.now(self.local_tz).strftime("%Y-%m-%d_%H-%M-%S")
                filename = f"{safe_name}_{safe_color}_{ts}.png"
                await self.page.screenshot(path=os.path.join(img_dir, filename), full_page=True)
                screenshot_name = filename
            except: pass
        else:
             screenshot_name = "Disabled"

        # Prepare Data
        now_utc = datetime.now(pytz.utc)
        date_str = now_utc.astimezone(self.local_tz).strftime('%Y-%m-%d')
        
        data = {
            "Product_Name": product_name,
            "Color": color_name,
            "Ton_Kho": ton_kho,
            "Gia_Niem_Yet": gia_niem_yet,
            "Gia_Khuyen_Mai": gia_khuyen_mai,
            "Date": date_str,
            "Khuyen_Mai": khuyen_mai,
            "Thanh_Toan": thanh_toan,
            "Link": self.url,
            "screenshot_name": screenshot_name
        }
        
        await write_to_csv(self.csv_path, data, self.csv_lock)
        print(f"Saved: {product_name} - {color_name} | Stock: {ton_kho} | Price: {gia_khuyen_mai}")

    async def process_colors(self):
        """Iterate through all color options."""
        # Strategy 0: Explicit ID (Best for Phones)
        color_wrapper = self.page.locator("#option-color")
        
        # Strategy 1: Look for explicit "Lựa chọn màu" section (Legacy/Generic)
        if await color_wrapper.count() == 0:
             color_wrapper = self.page.locator(COLOR_WRAPPER_SELECTOR)

        # Strategy 2: Fallback to generic product options container
        if await color_wrapper.count() == 0:
             color_wrapper = self.page.locator(".order-product .item").first.locator("..")
        
        # Strategy 3: Look for ".list-color" or ".list-variant" (Common in accessories)
        if await color_wrapper.count() == 0:
             color_wrapper = self.page.locator(".list-color")
        if await color_wrapper.count() == 0:
             color_wrapper = self.page.locator(".list-variant")
             
        # Get color items
        # If wrapper found, look inside. If not, look globally restricted to known containers
        if await color_wrapper.count() > 0:
            # Try specific item classes first
            if await color_wrapper.locator(".item-option").count() > 0:
                item_selector = ".item-option"
            else:
                item_selector = ".item"
            color_items = color_wrapper.locator(item_selector)
        else:
             # Fallback generic search
             item_selector = ".order-product .item"
             color_items = self.page.locator(item_selector)

        count = await color_items.count()
        
        if count == 0:
            print("  No color options found (strategies exhausted), scraping single variant.")
            # Even if no colors, we should try to get the product info
            # Just extract as "Unknown" color
            await self.scrape_variant("Unknown")
            return

        print(f"Found {count} color options.")
        
        for i in range(count):
            try:
                # Need to be careful about re-querying if DOM updates
                if await color_wrapper.count() > 0:
                     btn = color_wrapper.locator(item_selector).nth(i)
                else:
                     btn = self.page.locator(item_selector).nth(i)
                
                # Scroll parent/item
                if not await btn.is_visible():
                     try:
                        await btn.locator("..").scroll_into_view_if_needed(timeout=2000)
                     except: pass
                
                # Get Name
                color_name = ""
                # Try strong tag first
                if await btn.locator("strong").count() > 0:
                    color_name = await btn.locator("strong").first.inner_text()
                elif await btn.locator("span").count() > 0: # Accessories often use span
                    color_name = await btn.locator("span").first.inner_text()
                else:
                    color_name = await btn.inner_text()
                
                # Cleanup: Remove price if mixed in "Titan Sa Mạc\n30.000.000"
                if color_name:
                    color_name = color_name.split('\n')[0].strip()
                
                if not color_name: 
                    color_name = f"Option {i+1}"

                print(f"  Clicking: {color_name}")

                # Click
                # Check if it's already active? .item.active
                is_active = await btn.get_attribute("class")
                if is_active and "active" in is_active:
                     print("    (Already active)")
                else:
                    await btn.click(force=True)
                    await self.page.wait_for_timeout(1500)
                
                # Scrape
                await self.scrape_variant(color_name)
                
            except Exception as e:
                print(f"  Failed to process color [{i}]: {e}")

async def process_url(semaphore, browser, url, csv_path, csv_lock):
    async with semaphore:
        page = await browser.new_page(
            user_agent=USER_AGENT,
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1,
        )
        
        if BLOCK_IMAGES:
             await page.route("**/*", lambda route: route.abort() 
                if route.request.resource_type in ["image", "media", "font"] 
                else route.continue_())

        try:
            print(f"Processing: {url}")
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_timeout(5000) # Increased initial load wait

            interactor = HoangHaInteractor(page, url, csv_path, csv_lock)
            await interactor.process_colors()

        except Exception as e:
            print(f"Error processing {url}: {e}")
            # Debug screenshot on error
            try:
                 await page.screenshot(path=f"debug_error_{datetime.now().timestamp()}.png")
            except: pass
        finally:
            await page.close()

async def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.join(current_dir, '../content')
    
    local_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    date_str = datetime.now(local_tz).strftime('%Y-%m-%d')
    
    csv_path = setup_csv(base_path, date_str)
    csv_lock = asyncio.Lock()
    
    urls = total_links['hh_urls']
    if TEST_MODE:
        print("⚠️ TEST MODE ENABLED: Processing only 4 URLs")
        urls = urls[:4]
    
    print(f"Processing {len(urls)} URL(s).")
    
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TABS)
    
    async with async_playwright() as p:
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
            ],
            "ignore_default_args": ["--enable-automation"]
        }
        
        if proxy_server and os.environ.get("ENABLE_PROXY_HOANGHA", "False").lower() == "true":
             print(f"🌐 Using Proxy (HoangHa): {proxy_server}")
             launch_options["proxy"] = {"server": proxy_server}

        browser = await p.chromium.launch(**launch_options)
        
        tasks = [process_url(semaphore, browser, url, csv_path, csv_lock) for url in urls]
        await asyncio.gather(*tasks)
        await browser.close()

if __name__ == "__main__":
    start_time = datetime.now()
    asyncio.run(main())
    duration = datetime.now() - start_time
    print(f"Total time: {duration}")
