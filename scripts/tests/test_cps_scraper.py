#!/usr/bin/env python
"""
Test script for CellphoneS scraper promotion extraction.
Outputs to 6-cps-test.csv instead of production file.
"""
import asyncio
import os
import sys
import csv
from datetime import datetime

# Add crawler path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src/crawlers'))

from playwright.async_api import async_playwright

# Test URL - iPhone product with known promotions
TEST_URLS = [
    "https://cellphones.com.vn/iphone-14-pro-max.html",
    "https://cellphones.com.vn/iphone-13.html"
]

OUTPUT_FILE = "6-cps-test.csv"

async def main():
    # Import the modified scraper
    from utils.base_scraper import BaseScraper
    
    # We'll manually implement the scraping logic here to test
    import re
    
    PROMO_SELECTOR = "div.box-product-promotion"
    PAYMENT_PROMO_SELECTOR = "div.box-more-promotion"
    
    results = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        page = await context.new_page()
        
        for url in TEST_URLS:
            print(f"\n--- Testing: {url} ---")
            try:
                await page.goto(url, timeout=30000)
                await asyncio.sleep(2)  # Wait for dynamic content
                
                # Get product name
                product_name = await page.title()
                product_name = product_name.split("|")[0].strip() if "|" in product_name else product_name
                
                # Test NEW promotion extraction logic
                khuyen_mai = ""
                try:
                    promo_items = []
                    promo_container = page.locator(PROMO_SELECTOR)
                    if await promo_container.count() > 0:
                        promo_li = promo_container.locator("li")
                        li_count = await promo_li.count()
                        print(f"  Found {li_count} promo <li> items")
                        if li_count > 0:
                            for i in range(min(li_count, 10)):  # Limit to 10 items
                                text = await promo_li.nth(i).text_content()
                                if text and text.strip():
                                    promo_items.append(text.strip())
                        else:
                            text = await promo_container.text_content()
                            if text:
                                promo_items.append(text.strip())
                    khuyen_mai = " | ".join([re.sub(r'\n+', ' ', item) for item in promo_items if item])
                except Exception as e:
                    print(f"  Promo extraction error: {e}")
                
                # Test NEW payment promo extraction logic
                thanh_toan = ""
                try:
                    payment_items = []
                    payment_container = page.locator(PAYMENT_PROMO_SELECTOR)
                    if await payment_container.count() > 0:
                        payment_li = payment_container.locator("li")
                        li_count = await payment_li.count()
                        print(f"  Found {li_count} payment <li> items")
                        if li_count > 0:
                            for i in range(min(li_count, 10)):
                                text = await payment_li.nth(i).text_content()
                                if text and text.strip():
                                    payment_items.append(text.strip())
                        else:
                            text = await payment_container.text_content()
                            if text:
                                payment_items.append(text.strip())
                    thanh_toan = " | ".join([re.sub(r'\n+', ' ', item) for item in payment_items if item])
                except Exception as e:
                    print(f"  Payment extraction error: {e}")
                
                # Print results
                print(f"  Product: {product_name}")
                print(f"  Khuyen_Mai length: {len(khuyen_mai)} chars")
                print(f"  Khuyen_Mai preview: {khuyen_mai[:100]}..." if len(khuyen_mai) > 100 else f"  Khuyen_Mai: {khuyen_mai}")
                print(f"  Thanh_Toan length: {len(thanh_toan)} chars")
                print(f"  Thanh_Toan preview: {thanh_toan[:100]}..." if len(thanh_toan) > 100 else f"  Thanh_Toan: {thanh_toan}")
                
                results.append({
                    "Product_Name": product_name,
                    "Color": "Test",
                    "Khuyen_Mai": khuyen_mai,
                    "Thanh_Toan": thanh_toan,
                    "Link": url
                })
                
            except Exception as e:
                print(f"  ERROR: {e}")
        
        await browser.close()
    
    # Write results to test CSV
    if results:
        with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ["Product_Name", "Color", "Khuyen_Mai", "Thanh_Toan", "Link"]
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
            writer.writeheader()
            writer.writerows(results)
        print(f"\n✅ Saved {len(results)} results to {OUTPUT_FILE}")
    else:
        print("\n⚠️ No results to save")

if __name__ == "__main__":
    asyncio.run(main())
