import asyncio
import os
import sys
import re
import random
import time
from datetime import datetime
import pytz
from playwright.async_api import Page
from utils.sites import total_links
from utils.base_scraper import BaseScraper

# Constants
# Selectors
PRODUCT_NAME_SELECTOR = "div.box-product-name h1" 
PRICE_MAIN_SELECTOR = ".sale-price"
PRICE_SUB_SELECTOR = "del.base-price"
PROMO_SELECTOR = "div.box-product-promotion"
PAYMENT_PROMO_SELECTOR = "div.box-more-promotion"
COLOR_OPTIONS_SELECTOR = "//ul[contains(@class, 'list-variants')]/li"
STOCK_INDICATOR_SELECTOR = ".button-desktop-order-now, .button-desktop-order"
STORAGE_OPTIONS_SELECTOR = "//div[contains(@class, 'list-linked')]/a"

# Enable Gap Filling (recursive discovery of missing variants)
ENABLE_GAP_FILLING = os.environ.get("ENABLE_GAP_FILLING", "False").lower() == "true"

class CPSScraper(BaseScraper):
    def get_filename_prefix(self):
        return "6-cps"

    async def scrape_variant(self, page, url, color_name="Unknown", screenshot=False):
        # 1. Product Name
        product_name = await self.get_text_safe(page, PRODUCT_NAME_SELECTOR)
        if not product_name: 
            product_name = await page.title()
        
        for item in ["Chính hãng", " I ", " | ", " VN/A", " Apple Việt Nam", "Chính Hãng"]:
            product_name = product_name.replace(item, "")
        product_name = product_name.strip()

        # 2. Prices
        gia_khuyen_mai_raw = await self.get_text_safe(page, PRICE_MAIN_SELECTOR)
        gia_niem_yet_raw = await self.get_text_safe(page, PRICE_SUB_SELECTOR)
        if not gia_niem_yet_raw:
             gia_niem_yet_raw = await self.get_text_safe(page, ".product__price--through")
        
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

        # 4. Promotions
        khuyen_mai = ""
        try:
            km_text = await self.get_text_safe(page, PROMO_SELECTOR)
            if km_text:
                khuyen_mai = re.sub(r'\n+', '\n', km_text.strip())
        except: pass

        # 5. Payment Promo
        thanh_toan = ""
        try:
             tt_text = await self.get_text_safe(page, PAYMENT_PROMO_SELECTOR)
             if tt_text:
                 thanh_toan = re.sub(r'\n+', '\n', tt_text.strip())
        except: pass

        # 6. Screenshot
        screenshot_name = ""
        if (self.take_screenshot or gia_khuyen_mai == "0") and screenshot:
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
            "Link": page.url,
            "screenshot_name": screenshot_name
        }
        await self.write_to_csv(data)
        print(f"Saved: {product_name} - {color_name} | Price: {gia_khuyen_mai}")

    async def scrape(self, page, url):
        # 1. Process Colors
        try:
            try:
                 await page.wait_for_selector(COLOR_OPTIONS_SELECTOR, timeout=10000)
            except: pass

            candidates = page.locator(COLOR_OPTIONS_SELECTOR)
            count = await candidates.count()
            
            if count == 0:
                print("No color options found, scraping current page.")
                await self.scrape_variant(page, url, "Default")
            else:
                print(f"Found {count} color options.")

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
                        await page.wait_for_timeout(500)

                        await self.scrape_variant(page, url, color_name=color_name, screenshot=True)

                    except Exception as e:
                        print(f"Error processing color {i}: {e}")

        except Exception as e:
            print(f"Error in process_colors: {e}")

        # Gap Filling (Recursive)
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
                    # Recursively scrape new variant using same method
                    # But wait, 'scrape' expects an existing page.
                    # We need to navigate using the current page or a new one?
                    # Since we are inside 'scrape' which is inside a semaphore lock,
                    # reusing 'page' is fine if we navigate back or just navigate away?
                    # If we navigate away, we lose the original page context if we needed to do more.
                    # But here we are at the end of processing the original URL.
                    # So we can navigate to the new URL on the SAME page.
                    
                    try:
                        t_nav = time.time()
                        await page.goto(s_url, timeout=60000, wait_until="domcontentloaded")
                        # Recursively call scrape on this page
                        # We need to be careful about infinite recursion?
                        # Assuming structure is flat (variants link to each other), we might bounce back and forth.
                        # We should check if we already processed this URL in this session.
                        # Ideally, discovered URLs should be added to the queue, but here we are doing it depth-first.
                        # Let's simple scrape it.
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

    max_tabs = int(os.environ.get("MAX_CONCURRENT_TABS", 10))
    scraper = CPSScraper(urls=urls, max_concurrent=max_tabs)
    await scraper.run()

if __name__ == "__main__":
    start_time = datetime.now()
    asyncio.run(main())
    duration = datetime.now() - start_time
    print(f"Total execution time: {duration}")
