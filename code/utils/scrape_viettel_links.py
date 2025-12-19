import asyncio
from playwright.async_api import async_playwright

URLS = [
    "https://viettelstore.vn/dtdd-apple-iphone",
    "https://viettelstore.vn/tablet-apple-ipad",
    "https://viettelstore.vn/tbd-apple-watch"
]

async def scrape_viettel_links():
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
                # We will try to click this element repeatedly until it's no longer visible OR page height stops increasing
                
                max_clicks = 50 
                clicks = 0
                no_change_count = 0
                # selector for products (Broader)
                item_selector = "//div[contains(@class,'product-item')]//a"
                last_count = await page.locator(item_selector).count()
                
                while clicks < max_clicks:
                    try:
                        # Scroll to bottom
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await page.wait_for_timeout(2000)
                        
                        # Selector for the "Xem them" icon/button (Try JS Click on A tag)
                        show_more_btn = page.locator("#div_Danh_Sach_San_Pham_loadMore_btn a")
                        
                        if await show_more_btn.count() > 0 and await show_more_btn.is_visible():
                            print(f"Found 'Xem thêm' button, clicking via JS... ({clicks+1}/{max_clicks})")
                            await show_more_btn.first.evaluate("e => e.click()")
                            await page.wait_for_timeout(3000) # Wait for load
                            
                            # Check if content loaded by comparing ITEM COUNT
                            new_count = await page.locator(item_selector).count()
                            print(f"  Item count: {last_count} -> {new_count}")
                            
                            if new_count == last_count:
                                print(f"  Item count did not change. (Attempt {no_change_count + 1}/3)")
                                no_change_count += 1
                                if no_change_count >= 3:
                                    print("  Item count stuck for 3 attempts. Assuming end of list.")
                                    break
                            else:
                                no_change_count = 0
                                
                            last_count = new_count
                            clicks += 1
                        else:
                            print("No more 'Xem thêm' buttons found or reached end.")
                            break
                    except Exception as e:
                        print(f"Navigation/Click Error: {e}")
                        break

                # Extract Links
                # Extract Links
                # Use the same broad selector
                selector = "//div[contains(@class,'product-item')]//a"
                
                elements = page.locator(selector)
                count = await elements.count()
                print(f"Found {count} potential link elements on {url}.")
                
                for i in range(count):
                    href = await elements.nth(i).get_attribute("href")
                    if href:
                        if not href.startswith("http"):
                            href = "https://viettelstore.vn" + href
                        all_links.add(href)

            except Exception as e:
                print(f"Error processing {url}: {e}")
                continue
        
        # Output
        sorted_links = sorted(list(all_links))
        print("\n" + "="*30)
        print(f"TOTAL UNIQUE LINKS FOUND: {len(sorted_links)}")
        print("="*30)
        
        print("viettel_urls = [")
        for link in sorted_links:
            print(f"    '{link}',")
        print("]")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_viettel_links())
