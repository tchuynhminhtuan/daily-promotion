import asyncio
import os
import sys
from playwright.async_api import async_playwright

# Import sites
# Path: ../../code relative to this script
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../code')))
from utils import sites

OUTPUT_FILE = "discovered_cps_variants.txt"
STORAGE_SELECTOR = "//div[contains(@class, 'list-linked')]/a"
MAX_CONCURRENT_TABS = 15

async def discover_variants(semaphore, browser, url, existing_set, discovered_list, lock):
    async with semaphore:
        page = await browser.new_page()
        try:
            # Block images/fonts/css for speed
            await page.route("**/*", lambda route: route.abort() 
                if route.request.resource_type in ["image", "media", "font", "stylesheet"] 
                else route.continue_())

            try:
                await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            except:
                await page.close()
                return

            # Find variants
            links = page.locator(STORAGE_SELECTOR)
            count = await links.count()
            
            local_new = []
            for i in range(count):
                try:
                    href = await links.nth(i).get_attribute("href")
                    if href:
                        full = href if href.startswith("http") else "https://cellphones.com.vn" + href if href.startswith("/") else "https://cellphones.com.vn/" + href
                        full = full.split('?')[0]
                        if ".html" in full and full not in existing_set:
                            local_new.append(full)
                except: pass
            
            if local_new:
                async with lock:
                    for new_url in local_new:
                        if new_url not in discovered_list:
                            discovered_list.add(new_url)
                            print(f"[NEW] Found: {new_url}")

        except Exception as e:
            pass
        finally:
            await page.close()

async def main():
    urls = sites.total_links['cps_urls']
    existing_set = set(urls)
    discovered_list = set()
    lock = asyncio.Lock()
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TABS)

    print(f"Scanning {len(urls)} URLs for missing variants...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        tasks = [discover_variants(semaphore, browser, url, existing_set, discovered_list, lock) for url in urls]
        await asyncio.gather(*tasks)
        await browser.close()
    
    # Save to file
    with open(OUTPUT_FILE, "w") as f:
        for url in sorted(list(discovered_list)):
            f.write(url + "\n")
    
    print(f"\nScan Complete. Found {len(discovered_list)} missing variants.")
    print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())
