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
MAX_CONCURRENT_TABS = int(os.environ.get("MAX_CONCURRENT_TABS", 10))
TAKE_SCREENSHOT = os.environ.get("TAKE_SCREENSHOT", "False").lower() == "true"
BLOCK_IMAGES = os.environ.get("BLOCK_IMAGES", "True").lower() == "true"
HEADLESS = True
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

# --- Selectors ---
PRODUCT_NAME_SELECTOR = "h1.name-product"
PRICE_MAIN_SELECTOR = ".price-product .new-price"
PRICE_SUB_SELECTOR = ".price-product .old-price" 
PROMO_SELECTOR = ".box-promotion ol li"
COLOR_OPTIONS_SELECTOR = "ul.option-color-product li"
STOCK_INDICATOR_SELECTOR = "#btn-buy-now" 
PAYMENT_PROMO_SELECTOR = ".payment-promo .description" 

# --- Helper Functions ---
def setup_csv(base_path, date_str):
    output_dir = os.path.join(base_path, date_str)
    os.makedirs(output_dir, exist_ok=True)
    
    file_path = os.path.join(output_dir, f"3-viettel-{date_str}.csv")
    
    # Create img_viettel directory
    img_dir = os.path.join(output_dir, 'img_viettel')
    os.makedirs(img_dir, exist_ok=True)

    # Always overwrite or append logic? FPT/MW overwrite.
    if os.path.exists(file_path):
        try: os.remove(file_path)
        except: pass

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
        if await page.locator(selector).count() > 0:
            return await page.locator(selector).first.inner_text()
    except: pass
    return ""

class ViettelInteractor:
    def __init__(self, page, url, csv_path, csv_lock):
        self.page = page
        self.url = url
        self.csv_path = csv_path
        self.csv_lock = csv_lock
        self.processed_states = set() # Track unique states if needed

    async def remove_overlays(self):
        """Aggressively remove overlays and handle cookie consent."""
        try:
            # 1. Generic removal
            await self.page.evaluate("""
                document.querySelectorAll('.popup-modal, .overlay, .loading-cover').forEach(e => e.remove());
            """)
            
            # 2. Click "ĐỒNG Ý" or "Chấp nhận" button if present
            # Strategy: Find button with text
            await self.page.evaluate("""(() => {
                const buttons = Array.from(document.querySelectorAll('button, a, span, div'));
                const acceptButton = buttons.find(el => el.textContent.trim() === 'ĐỒNG Ý' || el.textContent.trim() === 'Chấp nhận');
                if (acceptButton && acceptButton.offsetParent !== null) { # Check visibility
                    acceptButton.click();
                }
            })()""")
        except: pass

    async def scrape_variant(self, color_name, forced_ton_kho=None):
        """Extract data for the CURRENT page state."""
        # Clean color name
        color_name = color_name.strip()
        
        # Avoid duplicate data for same color? 
        # (Assuming the main loop controls iterations, we scrape what we are asked)

        # 1. Product Name
        product_name = await get_text_safe(self.page, PRODUCT_NAME_SELECTOR)
        if not product_name: product_name = await self.page.title()
        
        # 2. Prices
        gia_khuyen_mai_raw = await get_text_safe(self.page, PRICE_MAIN_SELECTOR)
        gia_niem_yet_raw = await get_text_safe(self.page, PRICE_SUB_SELECTOR)
        
        if not gia_niem_yet_raw and gia_khuyen_mai_raw:
            gia_niem_yet_raw = gia_khuyen_mai_raw
            
        def clean_price(p):
            if not p: return "0"
            return str(p).replace("đ", "").replace("₫", "").replace(".", "").replace(",", "").strip()

        gia_khuyen_mai = clean_price(gia_khuyen_mai_raw)
        gia_niem_yet = clean_price(gia_niem_yet_raw)
        
        # 3. Stock
        ton_kho = "No"
        if forced_ton_kho is not None:
            ton_kho = forced_ton_kho
        else:
             try:
                content = await self.page.content()
                if "MUA NGAY" in content:
                    ton_kho = "Yes"
             except: pass
        if gia_khuyen_mai == "0": ton_kho = "No"

        # 4. Promo (Khuyen Mai)
        khuyen_mai = ""
        try:
            promos = []
            promo_elements = self.page.locator(PROMO_SELECTOR)
            count = await promo_elements.count()
            for i in range(count):
                text = await promo_elements.nth(i).inner_text()
                if text.strip():
                    cleaned = re.sub(r'\n+', '\n', text.strip()).replace('"', "'")
                    promos.append(cleaned)
            khuyen_mai = "\n".join(promos)
        except: pass
        
        # 5. Payment Promo (Thanh Toan)
        thanh_toan = ""
        try:
            payment_promos = []
            payment_elements = self.page.locator(PAYMENT_PROMO_SELECTOR)
            p_count = await payment_elements.count()
            for i in range(p_count):
                text = await payment_elements.nth(i).text_content() # Use text_content for hidden descriptions
                if text and text.strip():
                     cleaned = re.sub(r'\n+', '\n', text.strip()).replace('"', "'")
                     payment_promos.append(cleaned)
            thanh_toan = "\n".join(payment_promos)
        except: pass

        # 6. Screenshot
        screenshot_name = "Skipped"
        # Only take screenshot if Price is 0 OR Config requested
        if TAKE_SCREENSHOT or gia_khuyen_mai == "0":
             try:
                img_dir = os.path.join(os.path.dirname(self.csv_path), 'img_viettel')
                t_str = datetime.now().strftime("%H%M%S")
                safe_name = re.sub(r'[^\w]', '_', color_name)
                filename = f"VT_{t_str}_{safe_name}.png"
                await self.page.screenshot(path=os.path.join(img_dir, filename), full_page=True)
                screenshot_name = filename
             except: pass

        # Prepare Data
        data = {
            "Product_Name": product_name,
            "Color": color_name,
            "Ton_Kho": ton_kho,
            "Gia_Niem_Yet": gia_niem_yet,
            "Gia_Khuyen_Mai": gia_khuyen_mai,
            "Date": datetime.now(pytz.timezone('Asia/Ho_Chi_Minh')).strftime("%Y-%m-%d"),
            "Khuyen_Mai": khuyen_mai,
            "Thanh_Toan": thanh_toan,
            "Link": self.url,
            "screenshot_name": screenshot_name
        }
        
        await write_to_csv(self.csv_path, data, self.csv_lock)
        print(f"Saved: {product_name} - {color_name} | Price: {gia_khuyen_mai}")

    async def process_colors(self):
        """Iterate through all color options."""
        try:
            await self.remove_overlays()
            
            # STABILITY FIX: Wait for color options explicitly
            try:
                await self.page.locator("ul.option-color-product").wait_for(state="visible", timeout=5000)
                # Scroll into view to ensure elements are rendered/interactable
                await self.page.locator("ul.option-color-product").scroll_into_view_if_needed()
            except: pass

            # Get count with retry
            color_btns = self.page.locator(COLOR_OPTIONS_SELECTOR)
            count = await color_btns.count()
            
            if count == 0:
                print("  Retry finding colors...")
                await self.page.wait_for_timeout(2000)
                count = await color_btns.count()
            
            if count == 0:
                print("No color options found, scraping current state.")
                await self.scrape_variant("Unknown")
                return

            print(f"Found {count} color options.")
            
            for i in range(count):
                await self.remove_overlays()
                
                # Re-locate
                btn = self.page.locator(COLOR_OPTIONS_SELECTOR).nth(i)
                
                # Check visibility without forcing scroll on every item (parent scroll should cover it)
                if not await btn.is_visible(): 
                     # Only try to scroll parent again if item not visible
                     try:
                        await self.page.locator("ul.option-color-product").scroll_into_view_if_needed(timeout=2000)
                     except: pass
                
                # If still not visible, skip or try JS click? 
                # Let's try to proceed even if is_visible is false, as we force click anyway
                
                # Get Name
                color_name = await btn.inner_text()
                if not color_name:
                    # Try label title
                    label = btn.locator("label")
                    if await label.count() > 0:
                        color_name = await label.get_attribute("title")
                if not color_name: color_name = f"Color_{i}"
                
                # Check status
                is_disabled = False
                class_attr = await btn.get_attribute("class")
                if class_attr and "disabled" in class_attr: is_disabled = True
                
                # Click if not active? 
                # Viettel doesn't always have 'active' class on LI, maybe on Label label.checked?
                # Just click to be safe.
                
                if not is_disabled:
                    print(f"  Clicking: {color_name}")
                    try:
                        # Click the label inside if possible
                        targets = btn.locator("label")
                        if await targets.count() > 0:
                            await targets.first.click(force=True)
                        else:
                            await btn.click(force=True)
                        
                        # Wait for update
                        await self.page.wait_for_timeout(1000) # Wait for JS update
                        await self.remove_overlays()
                    except Exception as e:
                        print(f"    Click error: {e}")
                
                # Scrape
                await self.scrape_variant(color_name, forced_ton_kho="No" if is_disabled else None)
                
        except Exception as e:
            print(f"Error in process_colors: {e}")
            # Fallback
            await self.scrape_variant("Error_State")


async def process_url(semaphore, browser, url, csv_path, csv_lock):
    async with semaphore:
        page = await browser.new_page(
            user_agent=USER_AGENT,
            viewport={"width": 1920, "height": 1080}
        )
        
        if BLOCK_IMAGES:
            await page.route("**/*", lambda route: route.abort() 
                if route.request.resource_type in ["image", "media", "font"] 
                else route.continue_())

        try:
            print(f"Processing: {url}")
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_timeout(5000) # Init wait (Increased for stability)
            
            interactor = ViettelInteractor(page, url, csv_path, csv_lock)
            await interactor.process_colors()

        except Exception as e:
            print(f"Error processing {url}: {e}")
        finally:
            await page.close()

async def main():
    date_str = datetime.now(pytz.timezone('Asia/Ho_Chi_Minh')).strftime("%Y-%m-%d")
    base_path = os.path.join(current_dir, '../content')
    csv_path = setup_csv(base_path, date_str)
    csv_lock = asyncio.Lock()
    
    initial_urls = sites.total_links['vt_urls']
    if os.environ.get("TEST_MODE") == "True":
        print("⚠️ TEST MODE ENABLED: Processing 4 URLs")
        initial_urls = initial_urls[:4]
    
    print(f"Found {len(initial_urls)} URLs to process.")
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TABS)
    
    async with async_playwright() as p:
        # Proxy Setup (Standard)
        proxy_server = os.environ.get("PROXY_SERVER", "").strip()
        launch_options = {
            "headless": HEADLESS,
            "args": ["--disable-blink-features=AutomationControlled", "--window-size=1920,1080"],
            "ignore_default_args": ["--enable-automation"]
        }
        if proxy_server:
             # Basic parsing logic
            if "@" not in proxy_server and len(proxy_server.split(':')) == 4:
                 ip, port, user, pw = proxy_server.split(':')
                 proxy_server = f"http://{user}:{pw}@{ip}:{port}"
            if not proxy_server.startswith("http"): proxy_server = f"http://{proxy_server}"
            
            if os.environ.get("ENABLE_PROXY_VIETTEL", "False").lower() == "true":
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
