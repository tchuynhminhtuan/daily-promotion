import asyncio
from playwright.async_api import async_playwright

URL = 'https://fptshop.com.vn/tim-kiem?s=marshall&sort=noi-bat&hang-san-xuat=marshall'

async def debug_search():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print(f"Navigating to {URL}...")
        await page.goto(URL, timeout=60000, wait_until="domcontentloaded")
        await page.wait_for_timeout(5000) # Wait for JS rendering

        # Test common selectors
        print("\n--- Testing Selectors ---")
        
        # 1. Look for product cards by common grid classes
        grid_cand = page.locator("//div[contains(@class, 'grid')]")
        count = await grid_cand.count()
        print(f"Found {count} generic grid containers.")
        
        # 2. Look for product title/link hints
        links = page.locator("//div[contains(@class, 'product')]//a") # Loose guess
        c = await links.count()
        print(f"Generic product-like links found: {c}")
        
        # 3. Dump generic product container classes
        cards = page.locator("div.product-card, div.ProductCard_card__2C_sI, div.ProductCard_card__5R1J1")
        c2 = await cards.count()
        print(f"Explicit product cards found: {c2}")
        
        # 4. Dump HTML of the main content area (heuristically)
        # Try to find the container that holds the products
        main = page.locator("main")
        if await main.count() > 0:
            print("\n--- HTML Snippet of Main ---")
            html = await main.inner_html()
            # Find substring near some product name "Marshall"
            idx = html.find("Marshall")
            if idx != -1:
                start = max(0, idx - 500)
                end = min(len(html), idx + 500)
                print(html[start:end])
            else:
                print("Could not find 'Marshall' text in main content?!")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_search())
