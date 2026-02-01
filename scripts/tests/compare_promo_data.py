#!/usr/bin/env python
"""
Compare morning CSV promotion content with newly scraped data.
This script:
1. Reads the morning CSV files (original scraper output)
2. Re-scrapes a few products using the NEW iteration logic
3. Shows side-by-side comparison of Khuyen_Mai and Thanh_Toan content
"""
import asyncio
import os
import csv
import re
import pandas as pd
from playwright.async_api import async_playwright

# Morning CSV files
MORNING_CPS = "/Users/brucehuynh/GitHub/daily-promotion/data/raw/2026-02-01/6-cps-2026-02-01.csv"
MORNING_MW = "/Users/brucehuynh/GitHub/daily-promotion/data/raw/2026-02-01/2-mw-2026-02-01.csv"

# CPS Selectors
CPS_PROMO_SELECTOR = "div.box-product-promotion"
CPS_PAYMENT_SELECTOR = "div.box-more-promotion"

# MW Selectors
MW_PROMO_SELECTOR = ".promotions, .block__promo"
MW_PAYMENT_SELECTOR = "//div[@class='block__promo']/following-sibling::div[contains(@class, 'campaign')]"

async def scrape_with_new_logic(page, promo_selector, payment_selector, is_xpath=False):
    """Scrape using the NEW iteration-based logic"""
    khuyen_mai = ""
    thanh_toan = ""
    
    # Khuyen Mai
    try:
        promo_items = []
        promo_container = page.locator(promo_selector)
        if await promo_container.count() > 0:
            promo_li = promo_container.locator("li, .item, .promo-item")
            li_count = await promo_li.count()
            if li_count > 0:
                for i in range(min(li_count, 15)):
                    text = await promo_li.nth(i).text_content()
                    if text and text.strip():
                        promo_items.append(text.strip())
            else:
                text = await promo_container.text_content()
                if text:
                    promo_items.append(text.strip())
        khuyen_mai = " | ".join([re.sub(r'\n+', ' ', item) for item in promo_items if item])
    except Exception as e:
        print(f"  Promo error: {e}")
    
    # Thanh Toan
    try:
        payment_items = []
        payment_container = page.locator(payment_selector)
        if await payment_container.count() > 0:
            payment_li = payment_container.locator("li, .item")
            li_count = await payment_li.count()
            if li_count > 0:
                for i in range(min(li_count, 15)):
                    text = await payment_li.nth(i).text_content()
                    if text and text.strip():
                        payment_items.append(text.strip())
            else:
                text = await payment_container.text_content()
                if text:
                    payment_items.append(text.strip())
        thanh_toan = " | ".join([re.sub(r'\n+', ' ', item) for item in payment_items if item])
    except Exception as e:
        print(f"  Payment error: {e}")
    
    return khuyen_mai, thanh_toan

async def main():
    # 1. Read morning CSV files
    print("=" * 80)
    print("ANALYZING MORNING CSV DATA")
    print("=" * 80)
    
    # CPS Morning Data
    print("\n📊 CellphoneS Morning Data (6-cps-2026-02-01.csv):")
    try:
        cps_df = pd.read_csv(MORNING_CPS, sep=';', encoding='utf-8')
        print(f"  Total rows: {len(cps_df)}")
        
        # Count rows with non-empty Khuyen_Mai
        if 'Khuyen_Mai' in cps_df.columns:
            non_empty_km = cps_df['Khuyen_Mai'].notna() & (cps_df['Khuyen_Mai'] != '')
            print(f"  Rows with Khuyen_Mai: {non_empty_km.sum()}")
            # Average length
            avg_km_len = cps_df.loc[non_empty_km, 'Khuyen_Mai'].str.len().mean()
            print(f"  Avg Khuyen_Mai length: {avg_km_len:.0f} chars")
        
        if 'Thanh_Toan' in cps_df.columns:
            non_empty_tt = cps_df['Thanh_Toan'].notna() & (cps_df['Thanh_Toan'] != '')
            print(f"  Rows with Thanh_Toan: {non_empty_tt.sum()}")
            avg_tt_len = cps_df.loc[non_empty_tt, 'Thanh_Toan'].str.len().mean()
            print(f"  Avg Thanh_Toan length: {avg_tt_len:.0f} chars")
            
        # Sample a product
        sample = cps_df.iloc[0] if len(cps_df) > 0 else None
        if sample is not None:
            print(f"\n  Sample Product: {sample.get('Product_Name', 'N/A')}")
            print(f"  Sample Khuyen_Mai: {str(sample.get('Khuyen_Mai', ''))[:100]}...")
            print(f"  Sample Thanh_Toan: {str(sample.get('Thanh_Toan', ''))[:100]}...")
    except Exception as e:
        print(f"  Error reading CPS CSV: {e}")
    
    # MW Morning Data
    print("\n📊 Mobile World Morning Data (2-mw-2026-02-01.csv):")
    try:
        mw_df = pd.read_csv(MORNING_MW, sep=';', encoding='utf-8')
        print(f"  Total rows: {len(mw_df)}")
        
        if 'Khuyen_Mai' in mw_df.columns:
            non_empty_km = mw_df['Khuyen_Mai'].notna() & (mw_df['Khuyen_Mai'] != '')
            print(f"  Rows with Khuyen_Mai: {non_empty_km.sum()}")
            if non_empty_km.sum() > 0:
                avg_km_len = mw_df.loc[non_empty_km, 'Khuyen_Mai'].str.len().mean()
                print(f"  Avg Khuyen_Mai length: {avg_km_len:.0f} chars")
        
        if 'Thanh_Toan' in mw_df.columns:
            non_empty_tt = mw_df['Thanh_Toan'].notna() & (mw_df['Thanh_Toan'] != '')
            print(f"  Rows with Thanh_Toan: {non_empty_tt.sum()}")
            if non_empty_tt.sum() > 0:
                avg_tt_len = mw_df.loc[non_empty_tt, 'Thanh_Toan'].str.len().mean()
                print(f"  Avg Thanh_Toan length: {avg_tt_len:.0f} chars")
                
        sample = mw_df.iloc[0] if len(mw_df) > 0 else None
        if sample is not None:
            print(f"\n  Sample Product: {sample.get('Product_Name', 'N/A')}")
            print(f"  Sample Khuyen_Mai: {str(sample.get('Khuyen_Mai', ''))[:100]}...")
            print(f"  Sample Thanh_Toan: {str(sample.get('Thanh_Toan', ''))[:100]}...")
    except Exception as e:
        print(f"  Error reading MW CSV: {e}")
    
    # 2. Re-scrape with NEW logic
    print("\n" + "=" * 80)
    print("RE-SCRAPING WITH NEW ITERATION LOGIC")
    print("=" * 80)
    
    test_urls = [
        ("CPS", "https://cellphones.com.vn/iphone-13.html", CPS_PROMO_SELECTOR, CPS_PAYMENT_SELECTOR),
        ("CPS", "https://cellphones.com.vn/iphone-16-pro.html", CPS_PROMO_SELECTOR, CPS_PAYMENT_SELECTOR),
        ("MW", "https://www.thegioididong.com/dtdd/iphone-14", MW_PROMO_SELECTOR, MW_PAYMENT_SELECTOR),
    ]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        page = await context.new_page()
        
        for retailer, url, promo_sel, payment_sel in test_urls:
            print(f"\n🔍 [{retailer}] {url}")
            try:
                await page.goto(url, timeout=30000)
                await asyncio.sleep(2)
                
                km, tt = await scrape_with_new_logic(page, promo_sel, payment_sel)
                
                print(f"  NEW Khuyen_Mai: {len(km)} chars | Preview: {km[:80]}..." if len(km) > 80 else f"  NEW Khuyen_Mai: {len(km)} chars | {km}")
                print(f"  NEW Thanh_Toan: {len(tt)} chars | Preview: {tt[:80]}..." if len(tt) > 80 else f"  NEW Thanh_Toan: {len(tt)} chars | {tt}")
            except Exception as e:
                print(f"  Error: {e}")
        
        await browser.close()
    
    # 3. Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("""
If the NEW scraper output shows significantly MORE content (higher char counts)
than the morning CSV data, it means the new iteration logic is working correctly
and will extract more promotion details when the full scrapers are run.

Next steps:
1. Backup the morning CSV files
2. Run the full CPS and MW scrapers with: 
   python src/crawlers/6-Apple_CPS_playwright.py
   python src/crawlers/2-Apple_MW_playwright.py
3. Compare the new output with the backup
""")

if __name__ == "__main__":
    asyncio.run(main())
