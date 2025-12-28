import asyncio
from playwright.async_api import async_playwright

URL = "https://fptshop.com.vn/may-tinh-bang/ipad-air-11-m2-2024-wifi" # One of the failing items

async def debug_fpt():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
             user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
        
        print(f"Navigating to {URL}...")
        await page.goto(URL, timeout=60000)
        await page.wait_for_load_state("domcontentloaded")
        
        # Test 1: Count Containers using existing candidates
        print("\n--- TEST 1: Container Detection ---")
        candidates = [
             "//div[contains(@class, 'flex flex-col gap-1.5')]/span/following-sibling::div",
             "//div[contains(@class, 'flex flex-col gap-1.5')]/div/div",
             "//div[contains(@class, 'flex flex-wrap gap-2')]"
        ]
        
        for i, xpath in enumerate(candidates):
            count = await page.locator(xpath).count()
            print(f"Candidate {i} ('{xpath}'): Found {count} items")
            if count > 0:
                for j in range(count):
                    txt = await page.locator(xpath).nth(j).text_content()
                    print(f"  Item {j}: {txt[:50]}...")

        # Test 2: Dump relevant HTML area
        print("\n--- TEST 2: HTML Dump of Option Area ---")
        try:
            # Try to grab the parent of the buttons
            area = page.locator("//div[contains(@class, 'flex flex-col gap-1.5')]")
            count = await area.count()
            if count > 0:
                html = await area.first.inner_html()
                print(html[:1000])
            else:
                print("Could not find the parent option container 'flex flex-col gap-1.5'")
        except Exception as e:
            print(f"Error dumping HTML: {e}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_fpt())
