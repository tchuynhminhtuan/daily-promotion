import asyncio
from playwright.async_api import async_playwright

URL = "https://didongviet.vn/dien-thoai/iphone-17-pro-max-256gb.html"

async def inspect_page():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # Stealth
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print(f"Navigating to {URL}...")
        await page.goto(URL, timeout=60000, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000) # Let JS settle

        # 1. Product Name
        h1 = page.locator("h1")
        print(f"H1 Text: {await h1.inner_text()}")
        print(f"H1 Class: {await h1.get_attribute('class')}")

        # 2. JSON-LD Debug
        print("\n--- JSON-LD STRUCTURE ---")
        try:
            json_ld = await page.content()
            import re
            matches = re.findall(r'<script type="application/ld\+json">(.*?)</script>', json_ld, re.DOTALL)
            print(f"Found {len(matches)} JSON-LD blocks.")
            for i, match in enumerate(matches):
                print(f"Block {i}: {match[:200]}...")
        except Exception as e:
            print(f"JSON Error: {e}")

        # 3. Colors - Try finding container by label 'Màu sắc' again distinctively
        print("\n--- COLORS CONTAINER SEARCH ---")
        try:
            # Find the text "Màu sắc"
            lbl = page.locator("text=Màu sắc").first
            if await lbl.count() > 0:
                # Get parent, then look for siblings or children
                print("Found 'Màu sắc' label.")
                # Assumed structure: <div><p>Màu sắc</p><div>...buttons...</div></div>
                # Let's inspect the next sibling div
                container = lbl.locator("xpath=./following::div[1]")
                if await container.count() > 0:
                     print(f"Next Sibling HTML: {await container.evaluate('el => el.outerHTML')}")
        except: pass


        # 4. Storage by Text
        print("\n--- STORAGE BY TEXT ---")
        for st_txt in ["256GB", "512GB", "1TB"]:
            els = page.locator(f"text={st_txt}")
            count = await els.count()
            if count > 0:
                print(f"Found text '{st_txt}': {count} times")
                try:
                    p = els.first.locator("..")
                    print(f"  Parent Class: {await p.get_attribute('class')}")
                    gp = p.locator("..")
                    print(f"  Grandparent Class: {await gp.get_attribute('class')}")
                except: pass

        # 5. Promo content
        print("\n--- PROMO ---")
        # Look for "Khuyến mãi" header
        km = page.locator("text=Khuyến mãi")
        if await km.count() > 0:
            print("Found 'Khuyến mãi' text.")
            # Assume next sibling or parent container
            # Check containers with 'promo' in class
            promos = page.locator("[class*='promo']")
            print(f"Found {await promos.count()} elements with 'promo' in class")


        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_page())
