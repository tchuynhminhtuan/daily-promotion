import asyncio
import os
import sys
import re
from datetime import datetime
import pytz
from playwright.async_api import Page
from utils.sites import total_links
from utils.base_scraper import BaseScraper

# Constants
# Selectors
PRODUCT_NAME_SELECTOR = "h1.name-product"
PRICE_MAIN_SELECTOR = ".price-product .new-price"
PRICE_SUB_SELECTOR = ".price-product .old-price" 
PROMO_SELECTOR = ".box-promotion ol li"
COLOR_OPTIONS_SELECTOR = "ul.option-color-product li"
STOCK_INDICATOR_SELECTOR = "#btn-buy-now" 
PAYMENT_PROMO_SELECTOR = ".payment-promo .description" 

class ViettelScraper(BaseScraper):
    def get_filename_prefix(self):
        return "3-viettel"

    async def remove_overlays(self, page):
        """Aggressively remove overlays and handle cookie consent."""
        try:
            # 1. Generic removal
            await page.evaluate("""() => {
                document.querySelectorAll('.popup-modal, .overlay, .loading-cover').forEach(e => e.remove());
            }""")
            
            # 2. Click "ĐỒNG Ý" or "Chấp nhận" button if present
            await page.evaluate("""(() => {
                const buttons = Array.from(document.querySelectorAll('button, a, span, div'));
                const acceptButton = buttons.find(el => el.textContent.trim() === 'ĐỒNG Ý' || el.textContent.trim() === 'Chấp nhận');
                if (acceptButton && acceptButton.offsetParent !== null) {
                    acceptButton.click();
                }
            })()""")
        except: pass

    async def scrape_variant(self, page, url, color_name, forced_ton_kho=None):
        """Extract data for the CURRENT page state."""
        color_name = color_name.strip()
        
        # 2. Prices
        gia_khuyen_mai_raw = await self.get_text_safe(page, PRICE_MAIN_SELECTOR)
        gia_niem_yet_raw = await self.get_text_safe(page, PRICE_SUB_SELECTOR)
        
        if not gia_niem_yet_raw and gia_khuyen_mai_raw:
            gia_niem_yet_raw = gia_khuyen_mai_raw
            
        # JSON-LD Fallback
        if not gia_khuyen_mai_raw:
             try:
                 json_ld = await page.evaluate("""() => {
                    const script = document.querySelector('script[type="application/ld+json"]');
                    return script ? JSON.parse(script.innerText) : null;
                 }""")
                 if json_ld and "offers" in json_ld:
                     gia_khuyen_mai_raw = str(json_ld["offers"].get("price", ""))
             except: pass
            
        def clean_price(p):
            if not p: return "0"
            cleaned = re.sub(r'[^\d]', '', str(p).strip())
            return cleaned if cleaned else "0"

        gia_khuyen_mai = clean_price(gia_khuyen_mai_raw)
        gia_niem_yet = clean_price(gia_niem_yet_raw)
        
        # 3. Stock
        ton_kho = "No"
        if forced_ton_kho is not None:
            ton_kho = forced_ton_kho
        else:
             try:
                content = await page.content()
                if "MUA NGAY" in content:
                    ton_kho = "Yes"
             except: pass
        if gia_khuyen_mai == "0": ton_kho = "No"

        # 1. Product Name
        product_name = await self.get_text_safe(page, PRODUCT_NAME_SELECTOR)
        if not product_name: product_name = await page.title()
        
        product_name = product_name.replace(" - ViettelStore.vn", "").strip()

        # 4. Promo
        khuyen_mai = ""
        try:
            promos = []
            promo_elements = page.locator(PROMO_SELECTOR)
            count = await promo_elements.count()
            for i in range(count):
                text = await promo_elements.nth(i).inner_text()
                if text.strip():
                    cleaned = re.sub(r'\n+', '\n', text.strip()).replace('"', "'")
                    promos.append(cleaned)
            khuyen_mai = "\n".join(promos)
        except: pass
        
        # 5. Payment Promo
        thanh_toan = ""
        try:
            payment_promos = []
            payment_elements = page.locator(PAYMENT_PROMO_SELECTOR)
            p_count = await payment_elements.count()
            
            if p_count == 0:
                fallback = page.locator("#payment-promotion")
                if await fallback.count() > 0:
                     text = await fallback.inner_text()
                     if text.strip():
                         lines = [l.strip() for l in text.split('\n') if l.strip() and "Khuyến mãi" not in l]
                         payment_promos.extend(lines)
            else:
                for i in range(p_count):
                    text = await payment_elements.nth(i).text_content()
                    if text and text.strip():
                         cleaned = re.sub(r'\n+', '\n', text.strip()).replace('"', "'")
                         payment_promos.append(cleaned)
            
            thanh_toan = "\n".join(payment_promos)
        except: pass

        # 6. Screenshot
        screenshot_name = "Skipped"
        if self.take_screenshot or gia_khuyen_mai == "0":
             try:
                t_str = datetime.now().strftime("%H%M%S")
                safe_name = re.sub(r'[^\w]', '_', color_name)
                filename = f"VT_{t_str}_{safe_name}.png"
                await page.screenshot(path=os.path.join(self.img_dir, filename), full_page=True)
                screenshot_name = filename
             except: pass

        # Prepare Data
        data = {
            "Product_Name": product_name,
            "Color": color_name,
            "Ton_Kho": ton_kho,
            "Gia_Niem_Yet": gia_niem_yet,
            "Gia_Khuyen_Mai": gia_khuyen_mai,
            "Date": self.date_str,
            "Khuyen_Mai": khuyen_mai,
            "Thanh_Toan": thanh_toan,
            "Link": url,
            "screenshot_name": screenshot_name
        }
        
        await self.write_to_csv(data)
        print(f"Saved: {product_name} - {color_name} | Price: {gia_khuyen_mai}")

    async def scrape(self, page, url):
        await page.wait_for_timeout(5000) # Init wait

        try:
            await self.remove_overlays(page)
            
            try:
                await page.locator("ul.option-color-product").first.wait_for(state="visible", timeout=5000)
                await page.locator("ul.option-color-product").first.scroll_into_view_if_needed()
            except: pass

            color_ul = page.locator("ul.option-color-product").first
            color_btns = color_ul.locator("li")
            
            count = await color_btns.count()
            
            if count == 0:
                print("  Retry finding colors...")
                await page.wait_for_timeout(2000)
                count = await color_btns.count()
            
            if count == 0:
                print("No color options found, scraping current state.")
                await self.scrape_variant(page, url, "Unknown")
                return

            print(f"Found {count} color options.")
            
            for i in range(count):
                await self.remove_overlays(page)
                
                btn = color_ul.locator("li").nth(i)
                
                if not await btn.is_visible(): 
                     try:
                        await page.locator("ul.option-color-product").scroll_into_view_if_needed(timeout=2000)
                     except: pass
                
                color_name = await btn.inner_text()
                if not color_name:
                    label = btn.locator("label")
                    if await label.count() > 0:
                        color_name = await label.get_attribute("title")
                if not color_name: color_name = f"Color_{i}"
                
                is_disabled = False
                class_attr = await btn.get_attribute("class")
                if class_attr and "disabled" in class_attr: is_disabled = True
                
                label = btn.locator("label")
                if await label.count() > 0:
                     if await label.get_attribute("disabled"):
                         is_disabled = True
                     style = await label.get_attribute("style")
                     if style and "pointer-events: none" in style:
                         is_disabled = True
                
                if not is_disabled:
                    print(f"  Clicking: {color_name}")
                    try:
                        targets = btn.locator("label")
                        if await targets.count() > 0:
                            await targets.first.click(force=True)
                        else:
                            await btn.click(force=True)
                        
                        await page.wait_for_timeout(1000)
                        await self.remove_overlays(page)
                    except Exception as e:
                        print(f"    Click error: {e}")
                
                await self.scrape_variant(page, url, color_name, forced_ton_kho="No" if is_disabled else None)
                
        except Exception as e:
            print(f"Error in process_colors: {e}")
            await self.scrape_variant(page, url, "Error_State")

async def main():
    urls = total_links['vt_urls']
    specific_url = os.environ.get("SPECIFIC_URL")
    if specific_url:
        urls = [specific_url]
    elif os.environ.get("TEST_MODE") == "True":
        urls = urls[:4]
    
    max_tabs = int(os.environ.get("MAX_CONCURRENT_TABS", 10))
    scraper = ViettelScraper(urls=urls, max_concurrent=max_tabs)
    await scraper.run()

if __name__ == "__main__":
    start = datetime.now()
    asyncio.run(main())
    duration = datetime.now() - start
    print(f"Total execution time: {duration}")
