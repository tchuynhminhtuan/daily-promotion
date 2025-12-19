import asyncio
from playwright.async_api import async_playwright

URLS = [
    "https://fptshop.com.vn/apple/iphone",
    "https://fptshop.com.vn/apple/ipad",
    "https://fptshop.com.vn/apple/macbook",
    "https://fptshop.com.vn/apple/watch"
]

# User provided XPath
SELECTOR = "//h3[@class='h2-semibold mb:-mx-4 mb:px-4 mb:pt-4']/parent::div/following-sibling::div[@class='grid grid-cols-2 gap-2 pc:grid-cols-4 pc:gap-4']/div/div/div/a[@href]"

async def scrape_fpt_links():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Anti-bot
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        all_links = set()

        for url in URLS:
            print(f"Navigating to {url}...")
            try:
                await page.goto(url, timeout=60000, wait_until="domcontentloaded")
                await page.wait_for_timeout(3000)

                # Load More Loop (Generic "Xem thêm" button)
                while True:
                    try:
                        # Scroll to bottom
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await page.wait_for_timeout(2000)
                        
                        # Check for generic "Xem thêm" button
                        show_more_btn = page.locator("//button[contains(text(),'Xem thêm')] | //a[contains(text(),'Xem thêm')] | //div[contains(@class, 'btn-viewmore')]")
                        
                        count = await show_more_btn.count()
                        visible = False
                        for i in range(count):
                            if await show_more_btn.nth(i).is_visible():
                                print("Found 'Xem thêm' button, clicking...")
                                await show_more_btn.nth(i).click(force=True)
                                await page.wait_for_timeout(3000)
                                visible = True
                                break
                        
                        if not visible:
                            print("No more 'Xem thêm' buttons found or reached end.")
                            break
                    except Exception as e:
                        print(f"Navigation/Click Error: {e}")
                        break

                # Extract Links
                elements = page.locator(SELECTOR)
                count = await elements.count()
                print(f"Found {count} potential link elements on {url}.")
                
                for i in range(count):
                    href = await elements.nth(i).get_attribute("href")
                    if href:
                        if not href.startswith("http"):
                            href = "https://fptshop.com.vn" + href
                        all_links.add(href)

            except Exception as e:
                print(f"Error processing {url}: {e}")
                continue
        
        # Output
        sorted_links = sorted(list(all_links))
        print("\n" + "="*30)
        print(f"TOTAL UNIQUE LINKS FOUND: {len(sorted_links)}")
        print("="*30)
        
        print("fpt_urls = [")
        for link in sorted_links:
            print(f"    '{link}',")
        print("]")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_fpt_links())
