import asyncio
import os
import sys
import re
import random
import time
from datetime import datetime
import pytz
from playwright.async_api import Page
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.sites import total_links
from utils.base_scraper import BaseScraper

# Constants
# Selectors
PRODUCT_NAME_SELECTORS = [
    "div.box-product-name h1",
    "h1",
    "title",
    "[property='og:title']"
]
PRICE_MAIN_SELECTORS = [
    "//div[@class='smember-price-label']//div[@class='sale-price']",
    ".tpt---sale-price",
    ".sale-price",
    ".price",
    "[itemprop='price']",
    ".special-price"
]
PRICE_SUB_SELECTORS = [
    "del.base-price",
    ".product__price--through",
    ".old-price"
]
PROMO_SELECTOR = "div.box-product-promotion"
PAYMENT_PROMO_SELECTOR = "div.box-more-promotion"
COLOR_OPTIONS_SELECTOR = "//ul[contains(@class, 'list-variants')]/li"
STOCK_INDICATOR_SELECTOR = ".button-desktop-order-now, .button-desktop-order"
STOCK_INDICATOR_SELECTOR = ".button-desktop-order-now, .button-desktop-order"
STORAGE_OPTIONS_SELECTOR = "//div[contains(@class, 'list-linked')]/a"
TECH_SPECS_CONTAINER = "//div[@id='thong-so-ky-thuat']"
TECH_SPECS_BUTTON = "//div[@id='thong-so-ky-thuat']//button"
MODAL_SELECTORS = [".modal-technical", ".teleport-modal", ".modal", ".is-active"]

# Enable Gap Filling (recursive discovery of missing variants)
ENABLE_GAP_FILLING = os.environ.get("ENABLE_GAP_FILLING", "False").lower() == "true"

class CPSScraper(BaseScraper):
    def get_filename_prefix(self):
        return "6-cps"

    def get_fieldnames(self):
        fields = [
            "Product_Name", "Color", "Ton_Kho", "Gia_Niem_Yet", "Gia_Khuyen_Mai",
            "Date", "Khuyen_Mai", "Thanh_Toan", "Link"
        ]
        if os.environ.get("SCRAPE_SPECS") == "True":
            fields.append("Tech_Specs")
        fields.append("screenshot_name")
        return fields

    async def scrape_tech_specs(self, page):
        try:
            # 1. Expand (Click 'Xem tất cả')
            # Look for button inside container
            btn = page.locator(TECH_SPECS_BUTTON).first
            if await btn.count() > 0 and await btn.is_visible():
                await btn.click()
                await page.wait_for_timeout(1000)
            
            # 2. Try to find Modal
            # Common modal classes or look for a visible modal containing large text
            for selector in MODAL_SELECTORS:
                modals = page.locator(selector)
                count = await modals.count()
                for i in range(count):
                    m = modals.nth(i)
                    if await m.is_visible():
                        text = await m.inner_text()
                        if "Thông số kỹ thuật" in text and len(text) > 500:
                            return text.strip()

            # 3. Fallback to Container
            container = page.locator(TECH_SPECS_CONTAINER)
            if await container.count() > 0:
                return await container.inner_text()
            
            return ""
        except Exception as e:
            # print(f"Specs error: {e}")
            return ""

    async def scrape_variant(self, page, url, color_name="Unknown", screenshot=False):
        # 1. Product Name
        product_name = await self.get_element_text_with_fallbacks(page, PRODUCT_NAME_SELECTORS)
        if not product_name: 
            product_name = await page.title()
        
        for item in ["Chính hãng", " I ", " | ", " VN/A", " Apple Việt Nam", "Chính Hãng"]:
            product_name = product_name.replace(item, "")
        product_name = product_name.strip()

        # 2. Prices
        gia_khuyen_mai_raw = await self.get_element_text_with_fallbacks(page, PRICE_MAIN_SELECTORS)
        gia_niem_yet_raw = await self.get_element_text_with_fallbacks(page, PRICE_SUB_SELECTORS)

        gia_khuyen_mai = self.extract_price(gia_khuyen_mai_raw)
        gia_niem_yet = self.extract_price(gia_niem_yet_raw)
        
        if gia_niem_yet == 0 and gia_khuyen_mai != 0:
            gia_niem_yet = gia_khuyen_mai

        # 3. Stock
        ton_kho = "No"
        try:
            # Check Buy Button Text
            btn_loc = page.locator(STOCK_INDICATOR_SELECTOR).first
            if await btn_loc.count() > 0 and await btn_loc.is_visible():
                 btn_text = await btn_loc.inner_text()
                 if "MUA NGAY" in btn_text.upper():
                     ton_kho = "Yes"
            else:
                 cta_btns = page.locator("//button[contains(@class, 'btn-cta')]")
                 count = await cta_btns.count()
                 for i in range(count):
                     if await cta_btns.nth(i).is_visible():
                         txt = await cta_btns.nth(i).inner_text()
                         if "MUA NGAY" in txt.strip().upper():
                             ton_kho = "Yes"
                             break
        except: pass

        # 4. Promotions - Iterate over individual promo items
        khuyen_mai = ""
        try:
            promo_items = []
            promo_container = page.locator(PROMO_SELECTOR)
            if await promo_container.count() > 0:
                # First try to get individual list items
                promo_li = promo_container.locator("li")
                li_count = await promo_li.count()
                if li_count > 0:
                    for i in range(li_count):
                        text = await promo_li.nth(i).text_content()
                        if text and text.strip():
                            promo_items.append(text.strip())
                else:
                    # Fallback: get full container text
                    text = await promo_container.text_content()
                    if text:
                        promo_items.append(text.strip())
            khuyen_mai = " | ".join([re.sub(r'\n+', ' ', item) for item in promo_items if item])
        except: pass

        # 5. Payment Promo - Iterate over individual items
        thanh_toan = ""
        try:
            payment_items = []
            payment_container = page.locator(PAYMENT_PROMO_SELECTOR)
            if await payment_container.count() > 0:
                payment_li = payment_container.locator("li")
                li_count = await payment_li.count()
                if li_count > 0:
                    for i in range(li_count):
                        text = await payment_li.nth(i).text_content()
                        if text and text.strip():
                            payment_items.append(text.strip())
                else:
                    text = await payment_container.text_content()
                    if text:
                        payment_items.append(text.strip())
            thanh_toan = " | ".join([re.sub(r'\n+', ' ', item) for item in payment_items if item])
        except: pass

        # 5.1 Tech Specs
        tech_specs = ""
        if os.environ.get("SCRAPE_SPECS") == "True":
            try:
                tech_specs = await self.scrape_tech_specs(page)
            except: pass

        # 6. Screenshot
        screenshot_name = ""
        if (self.take_screenshot or gia_khuyen_mai == 0) and screenshot:
            try:
                safe_name = re.sub(r'[^\w\-\.]', '_', product_name)[:30]
                safe_color = re.sub(r'[^\w\-\.]', '_', color_name)[:10]
                fname = f"{safe_name}_{safe_color}_{datetime.now().strftime('%H%M%S')}.png"
                await page.screenshot(path=os.path.join(self.img_dir, fname), full_page=True)
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
            "Thanh_Toan": thanh_toan,
            "Link": page.url,
            "screenshot_name": screenshot_name
        }
        if os.environ.get("SCRAPE_SPECS") == "True":
            data["Tech_Specs"] = tech_specs
        await self.write_to_csv(data)
        print(f"Saved: {product_name} - {color_name} | Price: {gia_khuyen_mai}")

    async def set_location(self, page, location="Hà Nội"):
        try:
            # Check current location text
            btn = page.locator(".button__change-province").first
            if await btn.count() > 0:
                current_text = await btn.inner_text()
                if location in current_text:
                    return # Already set

                # Click to open modal
                await btn.click()
                await page.wait_for_timeout(1000)
                
                # Click location
                # Try specific modal selectors
                loc_option = page.locator(f"//div[contains(@class, 'modal')]//li/div/p[contains(text(), '{location}')]").first
                if await loc_option.count() == 0:
                     loc_option = page.locator(f"//div[contains(@class, 'modal')]//a[contains(text(), '{location}')]").first
                
                if await loc_option.count() > 0:
                    await loc_option.click()
                    await page.wait_for_timeout(2000) # Wait for reload/update
                    print(f"  Changed location to {location}")
        except Exception as e:
            print(f"  Location set error: {e}")

    async def scrape(self, page, url):
        locations = ["Hồ Chí Minh", "Hà Nội"]
        for loc in locations:
            # 0. Set Location
            await self.set_location(page, loc)

            # 1. Process Colors
            try:
                try:
                     await page.wait_for_selector(COLOR_OPTIONS_SELECTOR, timeout=10000)
                except: pass
    
                candidates = page.locator(COLOR_OPTIONS_SELECTOR)
                count = await candidates.count()
                
                if count == 0:
                    print(f"[{loc}] No color options found, scraping current page.")
                    # Pass location to scrape_variant name if needed? 
                    # Actually scrape_variant pulls data from page, which is now updated.
                    # We might want to tag the location in the saved data?
                    # The user just wants best price. 
                    # If we save rows, the analyzer picks min.
                    # Ideally we add 'Store' or 'Location' column? 
                    # Current schema: Product_Name, Color, Ton_Kho, etc.
                    # Using 'Product_Name' to distinguish? No, standard analysis uses columns.
                    # Just saving it as is works for 'min price'.
                    await self.scrape_variant(page, url, "Default")
                else:
                    print(f"[{loc}] Found {count} color options.")
    
                    for i in range(count):
                        try:
                            # Relocate to handle stale elements
                            btn = page.locator(COLOR_OPTIONS_SELECTOR).nth(i)
    
                            if not await btn.is_visible(): continue
    
                            color_name = ""
                            strong = btn.locator("strong")
                            if await strong.count() > 0:
                                color_name = await strong.first.inner_text()
                            else:
                                a_tag = btn.locator("a")
                                if await a_tag.count() > 0:
                                    color_name = await a_tag.get_attribute("title")
                                else:
                                    color_name = await btn.get_attribute("title")
    
                            if not color_name: color_name = f"Color_{i}"
    
                            await btn.click(force=True)
                            await page.wait_for_timeout(2000) # Increased wait to ensure page/DOM stability
    
                            await self.scrape_variant(page, url, color_name=color_name, screenshot=True)
    
                        except Exception as e:
                            print(f"[{loc}] Error processing color {i}: {e}")
    
            except Exception as e:
                print(f"[{loc}] Error in process_colors: {e}")

        # Gap Filling (Recursive) - Run once after location loops (URL discovery doesn't change)
        if ENABLE_GAP_FILLING:
            try:
                links = page.locator(STORAGE_OPTIONS_SELECTOR)
                count = await links.count()

                discovered_urls = []
                for i in range(count):
                    try:
                        href = await links.nth(i).get_attribute("href")
                        if href:
                            full = href if href.startswith("http") else "https://cellphones.com.vn" + href if href.startswith("/") else "https://cellphones.com.vn/" + href
                            full = full.split('?')[0]
                            if ".html" in full:
                                discovered_urls.append(full)
                    except: pass

                cps_set = set(total_links['cps_urls'])

                for s_url in set(discovered_urls):
                    if s_url == url.split('?')[0]: continue
                    if s_url in cps_set: continue

                    print(f"  Gap Filling: Found new variant {s_url}")
                    
                    try:
                        t_nav = time.time()
                        await page.goto(s_url, timeout=60000, wait_until="domcontentloaded")
                        await self.scrape(page, s_url)

                    except Exception as e:
                        print(f"    Error filling gap {s_url}: {e}")

            except Exception as e:
                print(f"  Storage discovery error: {e}")

async def main():
    urls = total_links['cps_urls']
    specific_url = os.environ.get("SPECIFIC_URL")
    if specific_url:
        urls = [specific_url]
    elif os.environ.get("TEST_MODE") == "True":
        urls = urls[:6]

    max_tabs = int(os.environ.get("MAX_CONCURRENT_TABS", 8))
    scraper = CPSScraper(urls=urls, max_concurrent=max_tabs)
    await scraper.run()

if __name__ == "__main__":
    start_time = datetime.now()
    asyncio.run(main())
    duration = datetime.now() - start_time
    print(f"Total execution time: {duration}")
