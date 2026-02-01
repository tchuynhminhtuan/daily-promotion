import asyncio
from playwright.async_api import async_playwright

URLS = [
    "https://fptshop.com.vn/apple/iphone",
    "https://fptshop.com.vn/apple/ipad",
    "https://fptshop.com.vn/apple/macbook",
    "https://fptshop.com.vn/apple/watch",
    'https://fptshop.com.vn/tim-kiem?s=marshall&sort=noi-bat&hang-san-xuat=marshall'
]

# User provided XPath
# Specific selector for structured Category pages (Apple iPhone, iPad, etc)
CATEGORY_SELECTOR = "//h3[@class='h2-semibold mb:-mx-4 mb:px-4 mb:pt-4']/parent::div/following-sibling::div[@class='grid grid-cols-2 gap-2 pc:grid-cols-4 pc:gap-4']/div/div/div/a[@href]"

# Broad selector for Search/Filter pages (e.g. Marshall search)
SEARCH_SELECTOR = "//div[contains(@class, 'grid') and (contains(@class, 'grid-cols-2') or contains(@class, 'grid-cols-3') or contains(@class, 'grid-cols-4'))]//a[@href]"

async def scrape_fpt_links():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Anti-bot
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        all_links = set()

        for url in URLS:
            print(f"Navigating to {url}...")
            
            # Determine which selector to use
            if "tim-kiem" in url or "?s=" in url:
                current_selector = SEARCH_SELECTOR
                is_search = True
            else:
                current_selector = CATEGORY_SELECTOR
                is_search = False

            try:
                await page.goto(url, timeout=60000, wait_until="domcontentloaded")
                await page.wait_for_timeout(3000)

                # Load More Loop (Generic "Xem thêm" button)
                # SKIP for Search Pages (handled better by default load, scrolling might break grid)
                while not is_search:
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
                elements = page.locator(current_selector)
                count = await elements.count()
                print(f"Found {count} potential link elements on {url}.")
                
                for i in range(count):
                    href = await elements.nth(i).get_attribute("href")
                    if href:
                        href = href.strip()
                        if not href.startswith("http"):
                            if not href.startswith("/"):
                                href = "/" + href
                            href = "https://fptshop.com.vn" + href
                        
                        # Filter out noise for search selector
                        if is_search:
                            lower_href = href.lower()
                            
                            # Forced Includes (Priority) - Keep valid product paths high, 
                            # BUT ensure they aren't actually news articles disguised (unlikely for FPT but good practice)
                            # Actually, it's safer to just run the exclusion list FIRST.
                            
                            # Rejection Logic (Strict)
                            # Filter out news, support, policies, etc.
                            if any(x in lower_href for x in ["/ho-tro/", "/tin-tuc", "/collection/", "/tos", "tel:", "zalo.me", "facebook.com", "youtube.com", "tiktok.com", "/gio-hang", "/kiem-tra-ho-so", "/danh-gia/"]):
                                continue
                            if href == "https://fptshop.com.vn" or href == "https://fptshop.com.vn/":
                                continue
                            if "google.com" in lower_href:
                                continue

                            # If it passed rejection, we accept it.
                            # Optional: We could check if it looks like a product (has 3 components or specific keywords), 
                            # but keeping it broad (allow list) is safer to not miss items.

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
