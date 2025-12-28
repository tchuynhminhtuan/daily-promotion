import asyncio
from playwright.async_api import async_playwright

URLS = [
    # "https://cellphones.com.vn/mobile/apple.html",
    # "https://cellphones.com.vn/tablet/ipad.html",
    # "https://cellphones.com.vn/laptop/mac.html",
    # "https://cellphones.com.vn/wearable/apple-watch.html"
    # Placeholder for Marshall or other categories
    "https://cellphones.com.vn/catalogsearch/result?q=marshall"
]

# Container Selectors: Identify the parent card or the link itself
CONTAINER_SELECTOR = "//div[contains(@class, 'product-info')] | //div[contains(@class, 'item-product')] | //div[contains(@class, 'product-item')] | //a[contains(@class, 'product__link')]"

# Exclusion Selector: Element indicating the product is out of stock / stopped
EXCLUSION_SELECTOR = ".product__more-info__item.notification.is-danger.is-light"

MAX_CLICKS = 5

async def scrape_cps_links():
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

                # Load More Loop
                clicks = 0
                while clicks < MAX_CLICKS:
                    try:
                        # Scroll to bottom
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await page.wait_for_timeout(2000)
                        
                        show_more_btn = page.locator("//a[contains(@class, 'btn-show-more')] | //div[contains(@class, 'btn-show-more')] | //button[contains(text(),'Xem thêm')]")
                        
                        count = await show_more_btn.count()
                        visible = False
                        for i in range(count):
                            if await show_more_btn.nth(i).is_visible():
                                print(f"Found 'Xem thêm' button, clicking... ({clicks+1}/{MAX_CLICKS})")
                                await show_more_btn.nth(i).click(force=True)
                                await page.wait_for_timeout(3000)
                                visible = True
                                clicks += 1
                                break
                        
                        if not visible:
                            print("No more 'Xem thêm' buttons found or reached end.")
                            break
                    except Exception as e:
                        print(f"Navigation/Click Error: {e}")
                        break

                # Extract Links Logic (Container Based)
                try:
                    await page.wait_for_selector(CONTAINER_SELECTOR, timeout=5000)
                except: pass

                containers = page.locator(CONTAINER_SELECTOR)
                count = await containers.count()
                print(f"Found {count} potential product containers on {url}.")
                
                accepted = 0
                excluded = 0
                
                for i in range(count):
                    try:
                        container = containers.nth(i)
                        
                        # 1. Check for Exclusion Element (Out of Stock)
                        # Explicitly use xpath= prefix to avoid CSS parsing errors
                        exclusion_xpath = "xpath=.//p[contains(@class, 'notification') and contains(@class, 'is-danger')]"
                        exclusion_check = await container.locator(exclusion_xpath).count()
                        
                        if exclusion_check > 0:
                            excluded += 1
                            continue

                        # 2. Extract Link
                        # Check element itself first (if it's an <a>), then children
                        href = await container.get_attribute("href")
                        
                        if not href:
                            link_element = container.locator("xpath=.//a").first
                            if await link_element.count() > 0:
                                href = await link_element.get_attribute("href")
                        
                        if href:
                            href = href.strip()
                            if not href.startswith("http"):
                                if not href.startswith("/"):
                                    href = "/" + href
                                href = "https://cellphones.com.vn" + href
                            
                            # Filter Logic: Keep valid product pages
                            if ".html" in href: 
                                all_links.add(href)
                                accepted += 1
                    except Exception as e:
                        print(f"Error processing container {i}: {e}")
                        pass
                
                print(f"  -> Accepted {accepted}, Excluded {excluded} links.")

            except Exception as e:
                print(f"Error processing {url}: {e}")
                continue
        
        # Output
        sorted_links = sorted(list(all_links))
        print("\n" + "="*30)
        print(f"TOTAL UNIQUE LINKS FOUND: {len(sorted_links)}")
        print("="*30)
        
        print("cps_urls = [")
        for link in sorted_links:
            print(f"    '{link}',")
        print("]")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_cps_links())
