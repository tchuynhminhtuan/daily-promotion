import asyncio
from playwright.async_api import async_playwright

URL = "https://hoanghamobile.com/tim-kiem?scope=&kwd=airpods"
SELECTOR = "//div[contains(@class, 'pj16-item')]/div/div[1]/div/a"

async def scrape_hoangha_links():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Anti-bot
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print(f"Navigating to {URL}...")
        try:
            await page.goto(URL, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
        except Exception as e:
            print(f"Error loading {URL}: {e}")
            await browser.close()
            return

        # Load More Loop (HoangHa uses "Xem thêm" button often)
        while True:
            try:
                # Scroll to bottom
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(2000)
                
                # Check for "Xem thêm" button
                # Selector: Generally generic, let's try a few common ones for HoangHa
                # Usually: .view-more or text 'Xem thêm'
                show_more_btn = page.locator("//a[contains(@class, 'view-more') or contains(text(), 'Xem thêm')]")
                
                count = await show_more_btn.count()
                visible = False
                for i in range(count):
                    if await show_more_btn.nth(i).is_visible():
                        print("Found 'Show more' button, clicking...")
                        await show_more_btn.nth(i).click()
                        await page.wait_for_timeout(3000)
                        visible = True
                        break
                
                if not visible:
                    print("No more 'Show more' buttons found or reached end.")
                    break
            except Exception as e:
                print(f"Navigation/Click Error: {e}")
                break

        # Extract Links
        links = set()
        elements = page.locator(SELECTOR)
        count = await elements.count()
        print(f"Found {count} potential link elements.")
        
        for i in range(count):
            href = await elements.nth(i).get_attribute("href")
            if href:
                if not href.startswith("http"):
                    href = "https://hoanghamobile.com" + href
                links.add(href)
        
        # Output
        sorted_links = sorted(list(links))
        print("\n" + "="*30)
        print(f"TOTAL UNIQUE LINKS FOUND: {len(sorted_links)}")
        print("="*30)
        
        print("hoangha_urls = [")
        for link in sorted_links:
            print(f"    '{link}',")
        print("]")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_hoangha_links())
