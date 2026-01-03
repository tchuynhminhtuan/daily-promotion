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
PRODUCT_NAME_SELECTORS = [
    ".product-name h1",
    "h1",
    ".product-name",
    "title",
    "[property='og:title']"
]
PROMO_SELECTOR = ".promotions, .block__promo"
PRICE_MAIN_SELECTORS = [
    ".box-price-present",
    ".bs_price strong",
    ".price-present",
    ".giamsoc-ol-price",
    ".center b",
    ".prods-price li span",
    ".box-price",
    "[itemprop='price']",
    ".price"
]
PRICE_SUB_SELECTORS = [
    ".box-price-old",
    ".bs_price em",
    ".price-old",
    ".old-price"
]
STORAGE_CONTAINER_SELECTOR = ".box03:not(.color), .group-box03:not(.color)" 
COLOR_CONTAINER_SELECTOR = ".box03.color, .group-box03.color, .scrolling_inner"

class MWScraper(BaseScraper):
    def get_filename_prefix(self):
        return "2-mw"

    def get_fieldnames(self):
        return [
            "Product_Name", "Color", "Ton_Kho", "Gia_Niem_Yet", "Gia_Khuyen_Mai",
            "Date", "Khuyen_Mai", "Thanh_Toan", "Link", 'screenshot_name'
        ]

    async def remove_overlays(self, page):
        """Aggressively remove MW specific overlays."""
        try:
            await page.evaluate("""() => {
                document.querySelectorAll('.popup-modal, .bg-black, .loading-cover, .loading').forEach(e => e.remove());
            }""")
        except: pass

    async def get_product_name(self, page, url):
        # Slower down the process to ensure name loads
        try:
            await page.wait_for_timeout(2000)
            await page.wait_for_selector("h1", timeout=3000)
        except: pass

        name = await self.get_element_text_with_fallbacks(page, PRODUCT_NAME_SELECTORS)
        if name: return name.strip()

        return "Error getting name"

    async def scrape_product_data(self, page, url, forced_color=None):
        product_name = await self.get_product_name(page, url)
        product_name = product_name.replace("Điện thoại ", "").replace("Laptop ", "").replace("Máy tính bảng ", "").strip()

        data = {
            "Product_Name": product_name,
            "Color": forced_color if forced_color else "Unknown",
            "Ton_Kho": "No",
            "Gia_Niem_Yet": 0,
            "Gia_Khuyen_Mai": 0,
            "Date": self.date_str,
            "Khuyen_Mai": "",
            "Thanh_Toan": "",
            "Link": url,
            "screenshot_name": "Skipped"
        }

        # Price Logic
        try:
            try:
                 await page.wait_for_selector(".bs_price strong, .price-present, .box-price-present", timeout=3000)
            except: pass

            shock_price = await self.get_element_text_with_fallbacks(page, PRICE_MAIN_SELECTORS)
            data["Gia_Khuyen_Mai"] = self.extract_price(shock_price)
            
            old_price = await self.get_element_text_with_fallbacks(page, PRICE_SUB_SELECTORS)
            data["Gia_Niem_Yet"] = self.extract_price(old_price)

            if data["Gia_Khuyen_Mai"] == 0:
                 data["Gia_Khuyen_Mai"] = data["Gia_Niem_Yet"]
            
            # Status Logic
            try:
                buy_btn_count = await page.locator("a, button, div").filter(has_text="Mua ngay").count()
                if data["Gia_Khuyen_Mai"] != 0 and buy_btn_count > 0:
                     data["Ton_Kho"] = "Yes"
                else:
                     data["Ton_Kho"] = "No"
            except Exception as e:
                if data["Gia_Khuyen_Mai"] != 0: data["Ton_Kho"] = "Yes"

            if data["Ton_Kho"] == "No":
                # Force Screenshot for debugging Price=0 or OOS
                if self.take_screenshot or True: # Force debug screenshot? Or adhere to config? adhering to config + specific logic
                     try:
                        filename = f"DEBUG_OOS_{product_name}_{data['Color']}_{datetime.now().strftime('%H%M%S')}.png"
                        await page.screenshot(path=os.path.join(self.img_dir, filename), full_page=True)
                        data['screenshot_name'] = filename
                     except: pass

        except Exception as e:
            print(f"Price error: {e}")

        try:
            promo = await self.get_text_safe(page, PROMO_SELECTOR)
            if promo: data["Khuyen_Mai"] = promo
        except: pass

        try:
            tt_selector = "//div[@class='block__promo']/following-sibling::div[contains(@class, 'campaign')]"
            tt = await self.get_text_safe(page, tt_selector)
            if tt: data["Thanh_Toan"] = tt.strip()
        except: pass

        await self.write_to_csv(data)
        print(f"Saved: {product_name} - {data['Color']} | Price: {data['Gia_Khuyen_Mai']}")

    async def process_color_options(self, page, url):
        try:
            robust_sel = ".box03.color .item, .group-box03 .item, .scrolling_inner .item, .box03__item.item"
            color_btns = page.locator(robust_sel)
            count = await color_btns.count()

            if count == 0:
                await self.scrape_product_data(page, url, forced_color="Default/Unknown")
                return

            for i in range(count):
                await self.remove_overlays(page)
                btn = page.locator(robust_sel).nth(i)
                if await btn.is_visible():
                    color_name = await btn.text_content()
                    color_name = color_name.strip()

                    if re.match(r'^\d+\s*(GB|TB)$', color_name, re.IGNORECASE):
                        continue

                    is_active = await btn.get_attribute("class")
                    if "act" not in is_active and "check" not in is_active:
                        try:
                            await btn.click(force=True, timeout=2000)
                            await page.wait_for_timeout(1000)
                        except: pass

                    await self.scrape_product_data(page, url, forced_color=color_name)
        except Exception as e:
            print(f"Color loop error: {e}")
            await self.scrape_product_data(page, url)

    async def process_storage_options(self, page, url):
        containers = page.locator(".box03, .group.desk, .group-box03")
        count = await containers.count()
        
        found_storage = False
        
        for i in range(count):
            cls = await containers.nth(i).get_attribute("class")
            
            if "color" in cls:
                continue
                
            btns = containers.nth(i).locator("a.item, div.item")
            btn_count = await btns.count()

            if btn_count > 1:
                found_storage = True
                
                for j in range(btn_count):
                    await self.remove_overlays(page)
                    container = page.locator(".box03").nth(i) # This logic from original might be brittle if containers index shifts
                    # Safer to re-locate generic list and pick nth(i)
                    container = page.locator(".box03, .group.desk, .group-box03").nth(i)
                    btn = container.locator("a.item, div.item").nth(j)
                    
                    current_url = page.url
                    
                    try:
                        await btn.click(force=True)
                        
                        try:
                            await page.wait_for_timeout(2000)
                            await page.wait_for_load_state("domcontentloaded", timeout=3000)
                        except: pass
                        
                        if page.url != current_url:
                            await self.remove_overlays(page)

                        await self.process_color_options(page, url)

                    except Exception as e:
                        print(f"    Error clicking storage option: {e}")

                return

        if not found_storage:
            await self.process_color_options(page, url)

    async def scrape(self, page, url):
        await self.remove_overlays(page)
        await self.process_storage_options(page, url)

async def main():
    urls = total_links['mw_urls']
    specific_urls = os.environ.get("SPECIFIC_URLS")
    specific_url = os.environ.get("SPECIFIC_URL")
    
    if specific_urls:
        urls = [u.strip() for u in specific_urls.split(',') if u.strip()]
    elif specific_url:
        urls = [specific_url]
    
    if specific_urls:
        urls = [u.strip() for u in specific_urls.split(',') if u.strip()]
    elif specific_url:
        urls = [specific_url]
    elif os.environ.get("TEST_MODE") == "True":
         urls = urls[:4]

    max_tabs = int(os.environ.get("MAX_CONCURRENT_TABS", 6))
    scraper = MWScraper(urls=urls, max_concurrent=max_tabs)
    await scraper.run()

if __name__ == "__main__":
    start = datetime.now()
    asyncio.run(main())
    duration = datetime.now() - start
    print(f"Total execution time: {duration}")
