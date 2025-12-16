import asyncio
from playwright.async_api import async_playwright
import time

URLS = [
    "https://didongviet.vn/dien-thoai-iphone.html",
]

# User provided selector
LINK_SELECTOR = "//div[@class='relative h-full']/a[@href]"

async def scrape_links():
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Stealth / Anti-bot
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        all_links = set()

        for url in URLS:
            print(f"Navigating to {url}...")
            try:
                await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            except Exception as e:
                print(f"Error loading {url}: {e}")
                continue
            
            # Handle "Xem thêm" (Show more) or Lazy Load
            # DDV usually has infinite scroll or "Xem thêm"
            # We will try scrolling to bottom a few times
            
            last_height = await page.evaluate("document.body.scrollHeight")
            retries = 0
            while True:
                # Scroll down to bottom
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                print("Scrolling...")
                
                # Check for "Xem thêm" button specifically if scrolling isn't enough
                # Attempt to find generic "Load more" buttons if they exist
                try:
                    # Common selectors for load more
                    # User requested specific selector: //p[@class='text-center text-14 font-medium text-black hover:text-ddv']
                    load_more = page.locator("//p[contains(@class, 'text-center text-14 font-medium text-black hover:text-ddv')] | //button[contains(text(), 'Xem thêm')] | //div[contains(text(), 'Xem thêm')]")
                    if await load_more.count() > 0 and await load_more.first.is_visible():
                        print("Clicking 'Xem thêm'...")
                        await load_more.first.click()
                        await page.wait_for_timeout(2000)
                except:
                    pass

                # Wait for load
                await page.wait_for_timeout(3000)
                
                new_height = await page.evaluate("document.body.scrollHeight")
                if new_height == last_height:
                    retries += 1
                    if retries >= 3: # Stop if no new content after 3 tries
                        break
                else:
                    retries = 0 # Reset if we found content
                    last_height = new_height
                    
                # Break verify if we have collected specific amount? No, user wants all.
                # Just loop until end.
                
            print("Finished scrolling/loading.")

            # Extract Links
            try:
                # Find product containers first to perform filtering
                # Based on LINK_SELECTOR = "//div[@class='relative h-full']/a[@href]"
                containers = page.locator("//div[@class='relative h-full']")
                count = await containers.count()
                print(f"Found {count} product containers.")
                
                for i in range(count):
                    container = containers.nth(i)
                    
                    # Check for exclusion element
                    # User requested to skip if this element exists
                    exclusion = container.locator("xpath=.//div[@class='text-12 font-medium text-ddv bg-red_transparent rounded px-2 py-1']")
                    if await exclusion.count() > 0:
                        # print("Skipping product with exclusion element")
                        continue

                    # Get link
                    link_el = container.locator("xpath=.//a[@href]").first
                    if await link_el.count() > 0:
                        href = await link_el.get_attribute('href')
                        if href:
                            if not href.startswith('http'):
                                href = "https://didongviet.vn" + href
                            
                            # Store unique links
                            all_links.add(href)
            except Exception as e:
                print(f"Extraction Error: {e}")
        
        # Deduplicate and sort
        sorted_links = sorted(list(all_links))
        
        print("\n" + "="*30)
        print(f"TOTAL UNIQUE LINKS FOUND: {len(sorted_links)}")
        print("="*30)
        
        # Format as requested python list
        print("ddv_urls = [")
        for link in sorted_links:
            print(f"    '{link}',")
        print("]")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_links())
