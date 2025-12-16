import asyncio
from playwright.async_api import async_playwright
import time

URLS = [
    "https://cellphones.com.vn/do-choi-cong-nghe/apple-watch.html",
]

async def scrape_links():
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Stealth / Anti-bot (Standard practice for these sites)
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
                    # Scroll to bottom to trigger lazy loading or finding the button
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(2000)
                    
                    # Check for "Xem thêm" button
                    # Selector might vary, commonly: .btn-show-more, or text "Xem thêm"
                    show_more_btn = page.locator("//div[contains(@class, 'cps-block-content')]//a[contains(@class, 'btn-show-more')] | //a[contains(text(), 'Xem thêm')]")
                    
                    count = await show_more_btn.count()
                    if count > 0 and await show_more_btn.first.is_visible():
                        print("Found 'Show more' button, clicking...")
                        await show_more_btn.first.click()
                        await page.wait_for_timeout(3000) # Wait for content to load
                    else:
                        print("No more 'Show more' buttons found or reached end.")
                        break
                except Exception as e:
                    print(f"Navigation Loop Error: {e}")
                    break

            # Extract Links
            # User suggested: //div[@class="product-info"]/a[@href]
            # Let's verify if that selector works, otherwise inspect broadly
            
            # Wait for product info to be visible
            try:
                await page.wait_for_selector("//div[contains(@class, 'product-info')]", timeout=5000)
            except: pass

            # Using the user's specific xpath idea but making it robust
            # We target the container first to check for exclusion criteria
            product_containers = page.locator('//div[contains(@class, "product-info")]')
            count = await product_containers.count()
            
            print(f"Found {count} product containers on {url}.")
            
            for i in range(count):
                container = product_containers.nth(i)
                
                # Check for exclusion criteria (User specified xpath)
                # We use a relative xpath starting with .// to search inside the container
                exclusion_node = container.locator("xpath=.//p[@class='product__more-info__item notification is-danger is-light']")
                if await exclusion_node.count() > 0:
                    # Skip this product
                    continue

                # Extract link from 'a' tag (assuming it's a direct child or descendant we want)
                # The original selector was .../a, so we look for 'a' inside the container
                link_element = container.locator("a").first
                href = await link_element.get_attribute('href')
                
                if href:
                    if not href.startswith('http'):
                        href = "https://cellphones.com.vn" + href
                    all_links.add(href)
        
        # Deduplicate and sort
        sorted_links = sorted(list(all_links))
        
        print("\n" + "="*30)
        print(f"TOTAL UNIQUE LINKS FOUND: {len(sorted_links)}")
        print("="*30)
        
        # Format as requested python list
        print("cps_urls = [")
        for link in sorted_links:
            print(f"    '{link}',")
        print("]")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_links())
