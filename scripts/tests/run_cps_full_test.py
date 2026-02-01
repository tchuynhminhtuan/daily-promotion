#!/usr/bin/env python
"""
Full scraper test for CellphoneS - outputs to 6-cps-full-test.csv
Uses the modified scraper with iteration-based promotion extraction.
"""
import asyncio
import os
import sys
from datetime import datetime

# Set environment to output to test file
os.environ["TEST_OUTPUT"] = "True"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src/crawlers'))

from utils.sites import total_links
from utils.base_scraper import BaseScraper
import re
import csv

# Import the modified CPSScraper
# We'll create a modified version that outputs to test file

class CPSTestScraper(BaseScraper):
    def get_filename_prefix(self):
        return "6-cps-full-test"  # Output to test file
    
    def get_fieldnames(self):
        return [
            "Product_Name",
            "Color",
            "Ton_Kho",
            "Gia_Niem_Yet",
            "Gia_Khuyen_Mai",
            "Date",
            "Khuyen_Mai",
            "Thanh_Toan",
            "Link",
            "screenshot_name"
        ]
        
    async def scrape_variant(self, page, url, color_name="Unknown", screenshot=False):
        PROMO_SELECTOR = "div.box-product-promotion"
        PAYMENT_PROMO_SELECTOR = "div.box-more-promotion"
        PRODUCT_NAME_SELECTORS = [
            "div.box-product-name h1",
            "h1",
            "title",
        ]
        PRICE_MAIN_SELECTORS = [
            "//div[@class='smember-price-label']//div[@class='sale-price']",
            ".tpt---sale-price",
            ".sale-price",
            ".price",
        ]
        PRICE_SUB_SELECTORS = [
            "del.base-price",
            ".product__price--through",
            ".old-price"
        ]
        STOCK_INDICATOR_SELECTOR = ".button-desktop-order-now, .button-desktop-order"
        
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
            btn_loc = page.locator(STOCK_INDICATOR_SELECTOR).first
            if await btn_loc.count() > 0 and await btn_loc.is_visible():
                 btn_text = await btn_loc.inner_text()
                 if "MUA NGAY" in btn_text.upper():
                     ton_kho = "Yes"
        except: pass

        # 4. Promotions - NEW ITERATION LOGIC
        khuyen_mai = ""
        try:
            promo_items = []
            promo_container = page.locator(PROMO_SELECTOR)
            if await promo_container.count() > 0:
                promo_li = promo_container.locator("li")
                li_count = await promo_li.count()
                if li_count > 0:
                    for i in range(li_count):
                        text = await promo_li.nth(i).text_content()
                        if text and text.strip():
                            promo_items.append(text.strip())
                else:
                    text = await promo_container.text_content()
                    if text:
                        promo_items.append(text.strip())
            khuyen_mai = " | ".join([re.sub(r'\n+', ' ', item) for item in promo_items if item])
        except: pass

        # 5. Payment Promo - NEW ITERATION LOGIC
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
            "screenshot_name": ""
        }
        await self.write_to_csv(data)
        print(f"Saved: {product_name} - {color_name} | KM: {len(khuyen_mai)} chars | TT: {len(thanh_toan)} chars")

    async def scrape(self, page, url):
        try:
            await page.goto(url, timeout=30000)
            await asyncio.sleep(1)
            
            # Get color options
            COLOR_OPTIONS_SELECTOR = "//ul[contains(@class, 'list-variants')]/li"
            color_opts = page.locator(COLOR_OPTIONS_SELECTOR)
            count = await color_opts.count()
            
            if count == 0:
                await self.scrape_variant(page, url, "Default")
            else:
                for i in range(count):
                    try:
                        opt = color_opts.nth(i)
                        color_name = await opt.get_attribute("data-name") or await opt.inner_text()
                        await opt.click()
                        await asyncio.sleep(0.5)
                        await self.scrape_variant(page, page.url, color_name)
                    except Exception as e:
                        print(f"Color variant error: {e}")
        except Exception as e:
            print(f"Page error: {e}")

async def main():
    # Only scrape first 5 URLs for testing
    links = total_links.get("cps", [])[:5]
    
    if not links:
        print("No CPS links found")
        return
    
    print(f"Scraping {len(links)} CPS products...")
    scraper = CPSTestScraper(take_screenshot=False)
    await scraper.run(links)
    print(f"\n✅ Results saved to: {scraper.csv_file}")

if __name__ == "__main__":
    asyncio.run(main())
