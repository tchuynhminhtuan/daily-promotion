import asyncio
from playwright.async_api import async_playwright

URLS = [
    "https://didongviet.vn/dien-thoai-iphone.html",
    "https://didongviet.vn/apple-ipad.html",
    "https://didongviet.vn/apple-macbook-imac.html",
    "https://didongviet.vn/dong-ho-apple-watch.html",
    "https://didongviet.vn/thiet-bi-am-thanh-apple.html",
]

async def scrape_ddv_links():
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

                # Loop to click "Xem thêm" (Load more) 
                while True:
                    try:
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await page.wait_for_timeout(2000)
                        
                        show_more_btn = page.locator("xpath=//button[contains(text(), 'Xem thêm') or contains(text(), 'Hiển thị thêm')]")
                        
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
                            print("No more 'Xem thêm' buttons found.")
                            break
                    except Exception as e:
                        print(f"Navigation Loop Error: {e}")
                        break

                # Extract standard product links
                # Di Dong Viet uses standard <a> tags with .html endings for products
                elements = page.locator("xpath=//a[contains(@href, '.html')]")
                count = await elements.count()
                
                print(f"Found {count} potential product links on {url}.")
                
                for i in range(count):
                    href = await elements.nth(i).get_attribute("href")
                    if href:
                        href = href.strip()
                        if not href.startswith("http"):
                            if not href.startswith("/"):
                                href = "/" + href
                            href = "https://didongviet.vn" + href
                        
                        lower_href = href.lower()
                        # Strict rejection logic (ignore news, collections, carts)
                        if any(x in lower_href for x in ["/tin-tuc", "/ho-tro", "/khuyen-mai", "/cart", "/thu-cu-doi-moi"]):
                            continue
                            
                        # Must contain one of the core categories to be valid Apple/Marshall
                        if any(x in lower_href for x in ["/dien-thoai/", "/may-tinh-bang/", "/apple-macbook-imac/", "/dong-ho-thong-minh/", "/thiet-bi-am-thanh/"]):
                            # Exclude cases that are just the category base
                            if href != "https://didongviet.vn/dien-thoai.html" and href != "https://didongviet.vn/may-tinh-bang.html":
                                all_links.add(href)

            except Exception as e:
                print(f"Error processing {url}: {e}")
                continue
        
        # Deduplicate and Output
        sorted_links = sorted(list(all_links))
        print("\n" + "="*30)
        print(f"TOTAL UNIQUE LINKS FOUND: {len(sorted_links)}")
        print("="*30)
        
        print("ddv_urls = [")
        for link in sorted_links:
            print(f"    '{link}',")
        print("]")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_ddv_links())
