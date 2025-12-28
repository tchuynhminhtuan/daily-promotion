import asyncio
import csv
import os
import sys
import re
from datetime import datetime
import pytz
from playwright.async_api import async_playwright

# Add root directory to sys.path to import utils.sites
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../code')))
from utils.sites import total_links

# --- Configuration ---
MAX_CONCURRENT_TABS = 5
HEADLESS = True
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

# --- Selectors ---
SELECTORS = {
    "fpt": {
        "name": "//h1",
        "price": "//span[contains(@class, 'h4-bold')]",
        "promo": "//div[contains(@class, 'flex flex-col gap-2')]",
        "stock": "//div[@id='detail-buying-btns']"
    },
    "mw": {
        "name": "h1",
        "price": ".bs_price strong, .price-present, .box-price-present",
        "stock": ".btn-buy, .btn-buy-now, .btn-add-cart",
        "promo": ".promotions, .block__promo"
    },
    "cps": {
        "name": "h1",
        "price": ".product__price--show, .box-info__box-price",
        "stock": "#btn-buy-now, .button-buy",
        "promo": ".box-promotion"
    }
}

async def get_text_safe(page, selector, timeout=5000):
    try:
        element = page.locator(selector).first
        if await element.is_visible(timeout=timeout):
            return await element.innerText()
    except: pass
    return ""

def clean_price(p_str):
    if not p_str: return "0"
    num = re.sub(r'[^\d]', '', p_str)
    return num if num else "0"

async def scrape_site(browser, site_key, urls, results, lock):
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TABS)
    
    async def process_url(url):
        async with semaphore:
            page = await browser.new_page(user_agent=USER_AGENT)
            # Block images for speed
            await page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "media", "font"] else route.continue_())
            
            try:
                print(f"[{site_key.upper()}] Scraping: {url}")
                await page.goto(url, timeout=60000, wait_until="domcontentloaded")
                await page.wait_for_timeout(2000)
                
                sel = SELECTORS.get(site_key, {})
                name = await get_text_safe(page, sel.get("name", "h1"))
                price_raw = await get_text_safe(page, sel.get("price", ""))
                promo = await get_text_safe(page, sel.get("promo", ""))
                
                # Stock check
                stock_count = await page.locator(sel.get("stock", "body")).count()
                stock_status = "Yes" if stock_count > 0 else "No"
                # Extra check for text "Hết hàng"
                body_text = await page.inner_text("body")
                if "Hết hàng" in body_text or "Ngừng kinh doanh" in body_text:
                    stock_status = "No"

                async with lock:
                    results.append({
                        "Site": site_key.upper(),
                        "Product Name": name.strip(),
                        "Price": clean_price(price_raw),
                        "Stock": stock_status,
                        "Promo": promo.strip().replace("\n", " | "),
                        "Link": url,
                        "Date": datetime.now(pytz.timezone('Asia/Ho_Chi_Minh')).strftime("%Y-%m-%d %H:%M")
                    })
            except Exception as e:
                print(f"Error {url}: {e}")
            finally:
                await page.close()

    tasks = [process_url(url) for url in urls]
    await asyncio.gather(*tasks)

async def main():
    # Load URLs
    fpt_urls = total_links.get("fpt_marshall_urls", [])
    mw_urls = total_links.get("mw_marshall_urls", [])
    cps_urls = total_links.get("cps_marshall_urls", [])
    
    results = []
    lock = asyncio.Lock()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS)
        
        await asyncio.gather(
            scrape_site(browser, "fpt", fpt_urls, results, lock),
            scrape_site(browser, "mw", mw_urls, results, lock),
            scrape_site(browser, "cps", cps_urls, results, lock)
        )
        
        await browser.close()
    
    # Save to CSV
    date_str = datetime.now(pytz.timezone('Asia/Ho_Chi_Minh')).strftime("%Y-%m-%d")
    output_path = os.path.join(os.path.dirname(__file__), f"content/{date_str}.csv")
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    if results:
        keys = results[0].keys()
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys, delimiter=";")
            writer.writeheader()
            writer.writerows(results)
        print(f"Successfully saved {len(results)} items to {output_path}")
    else:
        print("No results found.")

if __name__ == "__main__":
    asyncio.run(main())
