import asyncio
from playwright.async_api import async_playwright

URL = "https://fptshop.com.vn/may-tinh-xach-tay/macbook-pro-14-m5-2025-10cpu-10gpu-24gb-1tb-nano"

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        print(f"🌍 Navigating to {URL}...")
        await page.goto(URL, timeout=60000, wait_until="domcontentloaded")
        await page.wait_for_load_state("domcontentloaded")

        # 1. Old Selector
        old_xpath = "//div[contains(@class, 'flex flex-wrap gap-2')]"
        count_old = await page.locator(old_xpath).count()
        print(f"🛑 OLD Selector count: {count_old}")

        # 2. Previous New Selector (Macbook)
        new_xpath_mac = "//div[contains(@class, 'flex flex-col gap-1.5')]/div/div" 
        c_mac = await page.locator(new_xpath_mac).count()
        print(f"💻 MAC Selector count: {c_mac}")
        
        # 3. User Suggested Selector (Apple Watch) - Modified to find CONTAINER
        container_candidate_2 = "//div[contains(@class, 'flex flex-col gap-1.5')]/span/following-sibling::div"
        
        c2 = await page.locator(container_candidate_2).count()
        print(f"📦 Container Candidate 2 count: {c2}")
        
        # 6. DOM Inspection around Keywords
        print("\n🔍 DOM Inspection:")
        try:
            # Check for generic label text
            for keyword in ["Màu", "Kích", "Dung lượng"]:
                loc = page.locator(f"text={keyword}").first
                if await loc.count() > 0:
                    print(f"Found keyword '{keyword}'. Context:")
                    # Print parent HTML
                    try:
                        parent = loc.locator("..")
                        html = await parent.inner_html()
                        print(f"{html[:200]}...") # Print first 200 chars
                    except:
                        print("Could not print parent html")
                else:
                    print(f"Keyword '{keyword}' NOT FOUND.")
                    
            # Check body length
            content_len = len(await page.content())
            print(f"Page Content Length: {content_len}")
            
        except Exception as e:
            print(f"Error inspecting DOM: {e}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
