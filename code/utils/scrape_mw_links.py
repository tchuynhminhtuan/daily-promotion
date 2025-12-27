import asyncio
from playwright.async_api import async_playwright
import time

URLS = [
    # "https://www.thegioididong.com/dtdd-apple-iphone",
    # 'https://www.thegioididong.com/may-tinh-bang-apple-ipad',
    # 'https://www.thegioididong.com/laptop-apple-macbook',
    # 'https://www.thegioididong.com/dong-ho-thong-minh-apple',
    'https://www.thegioididong.com/phu-kien/marshall?key=marshall&sc=new#curl=marshall&mGenius=Marshall&o=9&pi=0'

]

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
            
            # Handle "Xem thêm" (Show more) button loop
            while True:
                try:
                    # Scroll to bottom
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(2000)
                    
                    # Check for "Xem thêm" button using USER SPECIFIED selector
                    show_more_btn = page.locator("//strong[contains(@class, 'see-more-btn')]")
                    
                    count = await show_more_btn.count()
                    if count > 0 and await show_more_btn.first.is_visible():
                        print("Found 'Xem thêm' button, clicking...")
                        await show_more_btn.first.click(force=True)
                        await page.wait_for_timeout(3000) # Wait for content to load
                    else:
                        print("No more 'Xem thêm' buttons found or reached end.")
                        break
                except Exception as e:
                    print(f"Navigation Loop Error: {e}")
                    break

            # Extract Links using USER SPECIFIED selector
            # Selector: //li[contains(@class, 'item')]/a[@href]
            try:
                # Wait for at least some items to be present
                await page.wait_for_selector("//li[contains(@class, 'item')]/a[@href]", timeout=5000)
            except: pass

            product_links = page.locator("//li[contains(@class, 'item')]/a[@href]")
            count = await product_links.count()
            
            print(f"Found {count} product matches on {url}.")
            
            for i in range(count):
                element = product_links.nth(i)
                href = await element.get_attribute('href')
                
                if href:
                    if not href.startswith('http'):
                        href = "https://www.thegioididong.com" + href
                    
                    # Optional: Filtering to ensure it's a product link not something else
                    # Update: Expanded to include iPad, Mac, Watch
                    if any(x in href for x in ["/dtdd/", "/laptop/", "/may-tinh-bang/", "/dong-ho-thong-minh/", ".html"]): 
                         all_links.add(href)
        
        # Deduplicate and sort
        sorted_links = sorted(list(all_links))
        
        print("\n" + "="*30)
        print(f"TOTAL UNIQUE LINKS FOUND: {len(sorted_links)}")
        print("="*30)
        
        # Format as requested python list
        print("mw_urls = [")
        for link in sorted_links:
            print(f"    '{link}',")
        print("]")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_links())
