import asyncio
import os
import sys
import re
import json
import time
from datetime import datetime
import pytz
from playwright.async_api import Page
from utils.sites import total_links
from utils.base_scraper import BaseScraper

# Constants
# Selectors
PRODUCT_NAME_SELECTORS = [
    "h1",
    ".top-product h1",
    "strong.name",
    "title",
    "[property='og:title']"
]
PRICE_CURRENT_SELECTORS = [
    ".box-price strong",
    ".current-price",
    ".price",
    "[itemprop='price']"
]
PRICE_OLD_SELECTORS = [
    ".box-price span",
    ".old-price"
]
COLOR_WRAPPER_SELECTOR = "//div[contains(@class, 'order-product')]//strong[contains(text(), 'Lựa chọn màu')]/parent::div/following-sibling::div"
STOCK_INDICATOR_SELECTOR = "a.btnQuickOrder"
PROMO_SELECTOR = "#product-promotion-content"
PAYMENT_PROMO_SELECTOR = ".promotion-slide-item"
STORE_COUNT_SELECTOR = ".box-stores-count p strong, .inventory-total, .inventory-label, h4:has-text('Cửa hàng còn hàng')"

class HoangHaScraper(BaseScraper):
    def get_filename_prefix(self):
        return "4-hoangha"

    def get_fieldnames(self):
        return [
            "Product_Name", "Color", "Ton_Kho", "Gia_Niem_Yet", "Gia_Khuyen_Mai",
            "Date", "Khuyen_Mai", "Thanh_Toan", "Store_Count", "Link", "screenshot_name"
        ]

    async def scrape_variant(self, page, url, color_name, forced_price=None):
        # 1. Product Name
        product_name = await self.get_element_text_with_fallbacks(page, PRODUCT_NAME_SELECTORS)
        
        if product_name:
            product_name = product_name.strip().split(" - ")[0]

        # 2. Stock (Ton_Kho)
        ton_kho = "Yes"
        try:
            btn = page.locator("a.btnQuickOrder, a.add-cart, .btn-buy").first
            if await btn.count() > 0:
                is_disabled = await btn.get_attribute("class")
                if is_disabled and "disabled" in is_disabled.lower():
                    ton_kho = "No"
                try:
                    text = await btn.text_content()
                    text = text.upper() if text else ""
                    if "HẾT HÀNG" in text or "LIÊN HỆ" in text or "TẠM HẾT" in text:
                        ton_kho = "No"
                except: pass
            else:
                ton_kho = "No"
        except:
            ton_kho = "No"

        # 3. Prices
        gia_niem_yet_raw = await self.get_element_text_with_fallbacks(page, PRICE_OLD_SELECTORS)
        
        if forced_price:
             gia_khuyen_mai = self.extract_price(forced_price)
        else:
             gia_khuyen_mai_raw = await self.get_element_text_with_fallbacks(page, PRICE_CURRENT_SELECTORS)
             gia_khuyen_mai = self.extract_price(gia_khuyen_mai_raw)
        
        gia_niem_yet = self.extract_price(gia_niem_yet_raw)
        if gia_niem_yet == 0 and gia_khuyen_mai != 0:
             gia_niem_yet = gia_khuyen_mai
        
        # 4. Promo
        khuyen_mai = ""
        try:
            promo_box = page.locator(PROMO_SELECTOR)
            if await promo_box.count() > 0:
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
                     text = await promo_box.inner_text()
                     if text:
                         khuyen_mai = re.sub(r'\n+', '\n', text.strip())
                
                khuyen_mai = khuyen_mai.replace('"', "'")
        except: pass
        
        # 5. Payment Promo
        thanh_toan = ""
        try:
            payment_promos = []
            payment_elements = page.locator(PAYMENT_PROMO_SELECTOR)
            count = await payment_elements.count()
            for i in range(count):
                data_attr = await payment_elements.nth(i).get_attribute("data-promotion")
                if data_attr:
                    try:
                        import html
                        decoded = html.unescape(data_attr)
                        promos_list = json.loads(decoded)
                        if isinstance(promos_list, list):
                            for p in promos_list:
                                if "Title" in p:
                                    clean_title = p["Title"].strip().replace('"', "'")
                                    payment_promos.append(clean_title)
                    except: pass
            
            if payment_promos:
                thanh_toan = "\n".join(payment_promos)
        except: pass

        # 6. Store Count
        store_count = "0"
        try:
            store_locs = page.locator(STORE_COUNT_SELECTOR)
            count = await store_locs.count()
            found_text = ""
            for i in range(count):
                try:
                    el = store_locs.nth(i)
                    if await el.is_visible():
                        txt = await el.text_content()
                        if txt and re.search(r'\d+', txt):
                            found_text = txt.strip()
                            break
                        if txt and "Cửa hàng" in txt:
                            found_text = txt.strip()
                except: pass
            
            if not found_text and count > 0:
                 try:
                    await store_locs.first.scroll_into_view_if_needed(timeout=1000)
                    count_text = await self.get_text_safe(page, STORE_COUNT_SELECTOR)
                    if count_text: found_text = count_text
                 except: pass

            if found_text:
                store_count = re.sub(r'[^\d]', '', found_text)
        except: pass

        # Screenshot
        screenshot_name = ""
        if self.take_screenshot:
            try:
                safe_name = re.sub(r'[^\w\-\.]', '_', product_name)
                safe_color = re.sub(r'[^\w\-\.]', '_', color_name)
                ts = datetime.now(self.local_tz).strftime("%Y-%m-%d_%H-%M-%S")
                filename = f"{safe_name}_{safe_color}_{ts}.png"
                await page.screenshot(path=os.path.join(self.img_dir, filename), full_page=True)
                screenshot_name = filename
            except: pass
        else:
             screenshot_name = "Disabled"

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
            "Store_Count": store_count,
            "Link": url,
            "screenshot_name": screenshot_name
        }
        
        await self.write_to_csv(data)
        print(f"Saved: {product_name} - {color_name} | Stock: {ton_kho} | Price: {gia_khuyen_mai} | Stores: {store_count}")

    async def scrape(self, page, url):
        await page.wait_for_timeout(2000) # Initial wait mostly for stability

        # Strategy 0: Explicit ID (Best for Phones)
        color_wrapper = page.locator("#option-color")
        
        # Strategy 1: Look for explicit "Lựa chọn màu" section
        if await color_wrapper.count() == 0:
             color_wrapper = page.locator(COLOR_WRAPPER_SELECTOR)

        # Strategy 2: Fallback to generic product options container
        if await color_wrapper.count() == 0:
             color_wrapper = page.locator(".order-product .item").first.locator("..")
        
        # Strategy 3: Look for ".list-color" or ".list-variant"
        if await color_wrapper.count() == 0:
             color_wrapper = page.locator(".list-color")
        if await color_wrapper.count() == 0:
             color_wrapper = page.locator(".list-variant")
             
        # Get color items
        if await color_wrapper.count() > 0:
            if await color_wrapper.locator(".item-option").count() > 0:
                item_selector = ".item-option"
            else:
                item_selector = ".item"
            color_items = color_wrapper.locator(item_selector)
        else:
             item_selector = ".order-product .item"
             color_items = page.locator(item_selector)

        count = await color_items.count()
        
        if count == 0:
            print("  No color options found, scraping single variant.")
            await self.scrape_variant(page, url, "Unknown")
            return

        print(f"Found {count} color options.")
        
        for i in range(count):
            try:
                if await color_wrapper.count() > 0:
                     btn = color_wrapper.locator(item_selector).nth(i)
                else:
                     btn = page.locator(item_selector).nth(i)
                
                if not await btn.is_visible():
                     try:
                        await btn.locator("..").scroll_into_view_if_needed(timeout=2000)
                     except: pass
                
                # Get Name
                color_name = ""
                if await btn.locator("strong").count() > 0:
                    color_name = await btn.locator("strong").first.inner_text()
                elif await btn.locator("span").count() > 0:
                    color_name = await btn.locator("span").first.inner_text()
                else:
                    color_name = await btn.inner_text()
                
                if color_name:
                    color_name = color_name.split('\n')[0].strip()
                
                if not color_name: 
                    color_name = f"Option {i+1}"
                
                forced_price = None
                try:
                    best_price = await btn.get_attribute("data-bestprice")
                    if best_price:
                        forced_price = best_price
                except: pass

                print(f"  Clicking: {color_name} (Price Override: {forced_price})")

                is_active_attr = await btn.get_attribute("class") or ""
                is_selected = "selected" in is_active_attr or "actived" in is_active_attr
                
                if is_selected:
                     await btn.click(force=True)
                     try:
                        await page.wait_for_timeout(1000)
                     except: pass
                else:
                    await btn.click(force=True)
                    try:
                        await page.wait_for_timeout(1500)
                    except: pass
                
                await self.scrape_variant(page, url, color_name, forced_price=forced_price)
                
            except Exception as e:
                print(f"  Failed to process color [{i}]: {e}")

async def main():
    urls = total_links['hh_urls']
    specific_url = os.environ.get("SPECIFIC_URL")
    if specific_url:
        urls = [specific_url]
    elif os.environ.get("TEST_MODE") == "True":
        urls = urls[:4]
    
    max_tabs = int(os.environ.get("MAX_CONCURRENT_TABS", 10))
    scraper = HoangHaScraper(urls=urls, max_concurrent=max_tabs)
    await scraper.run()

if __name__ == "__main__":
    start = datetime.now()
    asyncio.run(main())
    duration = datetime.now() - start
    print(f"Total execution time: {duration}")
