import asyncio
from playwright.async_api import async_playwright

URL = 'https://fptshop.com.vn/tim-kiem?s=marshall&sort=noi-bat&hang-san-xuat=marshall'

# Broad selector
SELECTOR = "//div[contains(@class, 'grid') and (contains(@class, 'grid-cols-2') or contains(@class, 'grid-cols-3') or contains(@class, 'grid-cols-4'))]//a[@href]"

async def debug_search_hrefs():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print(f"Navigating to {URL}...")
        await page.goto(URL, timeout=60000, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        
        elements = page.locator(SELECTOR)
        count = await elements.count()
        print(f"Found {count} potential link elements.")
        
        print("\n--- DUMPING HREFS ---")
        for i in range(count):
            href = await elements.nth(i).get_attribute("href")
            txt = (await elements.nth(i).inner_text() or "").replace("\n", " ").strip()[:50]
            print(f"[{i}] {txt} -> {href}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_search_hrefs())
