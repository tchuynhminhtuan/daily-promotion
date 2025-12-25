
import asyncio
import csv
import os
import random
import re
from datetime import datetime
import pytz
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
from utils.sites import total_links

# Configuration
OUTPUT_DIR = "content"
DDV_URLS = total_links['ddv_urls']

# Environment Variables
TAKE_SCREENSHOT = os.environ.get("TAKE_SCREENSHOT", "False").lower() == "true"
BLOCK_IMAGES = os.environ.get("BLOCK_IMAGES", "True").lower() == "true"
MAX_CONCURRENT_TABS = int(os.environ.get("MAX_CONCURRENT_TABS", 10))
HEADLESS = os.environ.get("HEADLESS", "True").lower() == "true"
TEST_MODE = os.environ.get("TEST_MODE", "False").lower() == "true"
SPECIFIC_URL = os.environ.get("SPECIFIC_URL")

USER_AGENT_LIST = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]

def setup_csv(base_path, date_str):
    output_dir = os.path.join(base_path, date_str)
    os.makedirs(output_dir, exist_ok=True)
    
    file_path = os.path.join(output_dir, f"5-ddv-{date_str}.csv")
    img_dir = os.path.join(output_dir, 'img_ddv')
    os.makedirs(img_dir, exist_ok=True)

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

class DDVInteractor:
    def __init__(self, page, url, csv_path, csv_lock):
        self.page = page
        self.url = url
        self.csv_path = csv_path
        self.csv_lock = csv_lock
        self.local_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        self.date_str = datetime.now(self.local_tz).strftime('%Y-%m-%d')
        self.base_product_name = ""

    async def get_text_safe(self, selector, timeout=500):
        try:
            loc = self.page.locator(selector).first
            if await loc.count() > 0 and await loc.is_visible(timeout=timeout):
                text = await loc.inner_text()
                if not text:
                    text = await loc.text_content()
                return text.strip() if text else ""
        except: pass
        return ""

    async def handle_popup(self):
        try:
            # Generic overlay closer
            close_btns = self.page.locator("button[aria-label='Close'], .close-popup, .popup-close, .ant-modal-close")
            if await close_btns.count() > 0:
                for i in range(await close_btns.count()):
                    if await close_btns.nth(i).is_visible():
                        await close_btns.nth(i).click()
        except: pass

    async def extract_stock_status(self):
        # Default to Yes. Check OOS signals.
        ton_kho = "Yes"
        
        # OOS Signal 1: "SẮP VỀ HÀNG" or "ĐĂNG KÝ NHẬN TIN" text above button
        try:
             # Look for specific text indicating OOS
            oos_text_loc = self.page.locator("text=SẮP VỀ HÀNG")
            if await oos_text_loc.count() > 0 and await oos_text_loc.first.is_visible():
                return "No"
            
            # OOS Signal 2: Buton Text is "ĐĂNG KÝ" instead of "MUA NGAY"
            # OOS Button Selector: button.ant-btn-primary with "ĐĂNG KÝ"
            btn_loc = self.page.locator("button.ant-btn-primary").first
            if await btn_loc.count() > 0:
                btn_text = await btn_loc.inner_text()
                if "ĐĂNG KÝ" in btn_text.upper() or "THÔNG TIN" in btn_text.upper():
                    return "No"
                
        except: pass
        return ton_kho

    async def extract_data(self, variant_color="Unknown", screenshot=False):
        # 1. Product Name
        if not self.base_product_name:
             self.base_product_name = await self.get_text_safe("h1")
             if not self.base_product_name: self.base_product_name = "Unknown"

        product_name = self.base_product_name

        # 2. Prices
        # Sale Price: Generic robust selector for size 24 bold (covers red-500, yellow-200, etc)
        # Selector: *[class*='text-24'][class*='font-bold']
        gia_khuyen_mai = 0
        gia_niem_yet = 0

        gkm_str = await self.get_text_safe(":is(p, div, span)[class*='text-24'][class*='font-bold']")
        if gkm_str:
             gia_khuyen_mai = int(re.sub(r'[^\d]', '', gkm_str)) if re.search(r'\d', gkm_str) else 0

        gny_str = await self.get_text_safe(".line-through")
        if gny_str:
             gia_niem_yet = int(re.sub(r'[^\d]', '', gny_str)) if re.search(r'\d', gny_str) else 0
        
        # JSON-LD Fallback if CSS failed
        if gia_khuyen_mai == 0:
            try:
                json_ld = await self.page.evaluate("""() => {
                    const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                    for (const script of scripts) {
                        try {
                            const data = JSON.parse(script.innerText);
                            // Handle single product or graph
                            const product = data['@type'] === 'Product' ? data : 
                                          (data['@graph'] ? data['@graph'].find(g => g['@type'] === 'Product') : null);
                            
                            if (product && product.offers) {
                                // offer can be list or object
                                const offer = Array.isArray(product.offers) ? product.offers[0] : product.offers;
                                return offer.price || offer.highPrice || offer.lowPrice;
                            }
                        } catch(e){}
                    }
                    return null;
                }""")
                if json_ld:
                    gia_khuyen_mai = int(float(str(json_ld)))
            except: pass

        if gia_niem_yet == 0 and gia_khuyen_mai > 0:
            gia_niem_yet = gia_khuyen_mai

        # 3. Stock
        ton_kho = await self.extract_stock_status()

        # 3.1 Store Count
        store_count = "0"
        try:
             count_loc = self.page.locator("//div[@class='py-2']/p/span")
             if await count_loc.count() > 0:
                 count_text = await count_loc.inner_text()
                 # Expected: "Còn 3 cửa hàng" or just "3"
                 if count_text:
                     store_count = re.sub(r'[^\d]', '', count_text)
        except: pass

        # 4. Promotions
        # Click "View More" if exists to reveal full content
        try:
            view_more_btn = self.page.locator("//button[contains(@class, 'w-full')]/p[contains(text(),'Xem thêm')] | //button[contains(@class, 'w-full')]/p[contains(text(),'Xem tất cả')]").first
            # Or generic path suggested: //button[contains(@class, 'w-full')]/p
            if await view_more_btn.count() == 0:
                 view_more_btn = self.page.locator("//button[contains(@class, 'w-full')]/p").first
            
            if await view_more_btn.count() > 0 and await view_more_btn.is_visible():
                await view_more_btn.click(force=True)
                await self.page.wait_for_timeout(500)
        except: pass

        khuyen_mai = ""
        try:
             # Common promo area: div.border.rounded-lg.overflow-hidden.w-full
             km_loc = self.page.locator("div.border.rounded-lg.overflow-hidden.w-full").first
             if await km_loc.count() > 0:
                 khuyen_mai = await km_loc.inner_text()
                 khuyen_mai = khuyen_mai.strip()
        except: pass

        thanh_toan = "" 
        try:
            # Selector: //div[@class='flex w-full flex-col items-start justify-start bg-white p-2']
            tt_loc = self.page.locator("//div[@class='flex w-full flex-col items-start justify-start bg-white p-2']")
            count = await tt_loc.count()
            tt_texts = []
            for i in range(count):
                if await tt_loc.nth(i).is_visible():
                     text = await tt_loc.nth(i).inner_text()
                     if text:
                         tt_texts.append(text.strip())
            
            if tt_texts:
                thanh_toan = "\n".join(tt_texts)
        except: pass 

        # 5. Screenshot
        screenshot_name = ""
        if screenshot and TAKE_SCREENSHOT:
            try:
                img_dir = os.path.join(os.path.dirname(self.csv_path), 'img_ddv')
                safe_name = re.sub(r'[^\w\-\.]', '_', product_name)[:30]
                safe_color = re.sub(r'[^\w\-\.]', '_', variant_color)[:10]
                fname = f"{safe_name}_{safe_color}_{datetime.now().strftime('%H%M%S')}.png"
                await self.page.screenshot(path=os.path.join(img_dir, fname), full_page=True)
                screenshot_name = fname
            except: pass
            
        # 6. Save
        data = {
            "Product_Name": product_name,
            "Color": variant_color,
            "Ton_Kho": ton_kho,
            "Store_Count": store_count, 
            "Gia_Niem_Yet": gia_niem_yet,
            "Gia_Khuyen_Mai": gia_khuyen_mai,
            "Date": self.date_str,
            "Khuyen_Mai": khuyen_mai,
            "Thanh_Toan": thanh_toan,
            "Other_promotion": "",
            "Link": self.page.url,
            "screenshot_name": screenshot_name
        }
        await write_to_csv(self.csv_path, data, self.csv_lock)
        print(f"Saved: {product_name} - {variant_color} | Stock: {ton_kho} | Price: {gia_khuyen_mai}")

    async def process_colors_grid(self):
        # Improved Strategy:
        # 1. Look for specific color container if possible. 
        # 2. Iterate ALL div.cursor-pointer.rounded elements (relaxed from .border).
        # 3. Filter by checking if they contain "GB/TB" (storage) or "Mua" (button).
        # 4. Check if they have some border class (border, border-1, border-red-500 etc)
        
        candidates = self.page.locator("div.cursor-pointer.rounded")
        count = await candidates.count()
        
        valid_colors = []
        for i in range(count):
            try:
                el = candidates.nth(i)
                if not await el.is_visible(): continue
                
                # Check for border-like class
                classes = await el.get_attribute("class") or ""
                if "border" not in classes: continue

                # Get all text inside
                text = await el.text_content()
                clean_text = text.strip()
                
                if not clean_text: continue
                
                # Filter out Storage (contains GB/TB)
                # Use simple string check as regex \b missed "128GB"
                if "GB" in clean_text.upper() or "TB" in clean_text.upper(): continue
                
                # Filter out Buy buttons
                if "MUA" in clean_text.upper() or "ĐĂNG KÝ" in clean_text.upper(): continue
                if "TRẢ GÓP" in clean_text.upper(): continue

                # Filter out "Price" boxes ONLY if they don't look like colors
                # Some sites put price INSIDE color box. That is fine. 
                # But if it's JUST price, maybe not. 
                # DDV color boxes usually have Name + Price. 
                
                valid_colors.append((clean_text, i))
            except: continue
            
        # Deduplicate
        unique_colors = {}
        for txt, idx in valid_colors:
            # Simple deduplication by text content
            # If "Red 10tr" and "Red 10tr", same.
            if txt not in unique_colors:
                unique_colors[txt] = idx
                
        if not unique_colors:
            # Fallback: maybe no colors (single variant)
            await self.extract_data(variant_color="Default")
            return

        for color_text, idx in unique_colors.items():
            try:
                el = self.page.locator("div.cursor-pointer.rounded").nth(idx)
                
                # Check disabled
                classes = await el.get_attribute("class") or ""
                if "cursor-not-allowed" in classes or "!grayscale" in classes:
                     pass # Click anyway to capture OOS status/price if possible?
                
                # Scroll into view
                await el.scroll_into_view_if_needed()
                
                # Click
                await el.click(force=True)
                # Optimize: Reduced wait from 800ms to 300ms
                await self.page.wait_for_timeout(300) # Wait for SPA update
                
                # Extract Color Name from the text (remove price if needed)
                # Usually text is "Màu X \n 10.000.000". We want "Màu X".
                # Simple split by newline or regex
                color_name = color_text.split('\n')[0].strip()
                # Remove common prefixes like "Màu"
                color_name = color_name.replace("Màu", "").strip()

                await self.extract_data(variant_color=color_name, screenshot=True)
                
            except Exception as e:
                print(f"Error processing color {color_text}: {e}")

async def process_url(semaphore, browser, url, csv_path, csv_lock):
    async with semaphore:
        page = await browser.new_page(
            user_agent=random.choice(USER_AGENT_LIST),
            viewport={"width": 1920, "height": 1080},
            locale="vi-VN"
        )
        
        # Block images
        if BLOCK_IMAGES:
            await page.route("**/*", lambda route: route.abort() 
                if route.request.resource_type in ["image", "media", "font"] 
                else route.continue_())

        print(f"Processing: {url}")
        try:
            try:
                await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            except:
                print(f"Retry loading {url}")
                await page.goto(url, timeout=60000, wait_until="domcontentloaded")

            # OPTIMIZATION: Removed recursive storage discovery loop.
            # We strictly process the URL provided in the input list.
            target_urls = [url]

            for s_url in target_urls:
                try:
                    # Navigate if different from current
                    if s_url != page.url:
                        await page.goto(s_url, timeout=60000, wait_until="domcontentloaded")
                    
                    interactor = DDVInteractor(page, s_url, csv_path, csv_lock)
                    await interactor.handle_popup()
                    await interactor.process_colors_grid()
                    
                except Exception as e:
                    print(f"Error processing storage variant {s_url}: {e}")

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
    
    urls_to_process = DDV_URLS
    
    if SPECIFIC_URL:
        print(f"⚠️ PROCESSING SPECIFIC URL: {SPECIFIC_URL}")
        urls_to_process = [SPECIFIC_URL]
    elif TEST_MODE:
        print("⚠️ TEST MODE: Processing first 4 URLs only.")
        urls_to_process = DDV_URLS[:4]

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
        
        if proxy_server and os.environ.get("ENABLE_PROXY_DDV", "False").lower() == "true":
             print(f"🌐 Using Proxy (DDV): {proxy_server}")
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
