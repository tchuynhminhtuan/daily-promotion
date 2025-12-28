import asyncio
from playwright.async_api import async_playwright

URL = "https://fptshop.com.vn/may-tinh-xach-tay/macbook-pro-14-m5-2025-10cpu-10gpu-24gb-1tb-nano"

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        print(f"🌍 Navigating to {URL}...")
        try:
            await page.goto(URL, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_load_state("domcontentloaded")
        except:
            print("timeout loading page")

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
        
        # 4. INSPECTION
        target_xpath = ""
        if c2 > 0:
            target_xpath = container_candidate_2
            print("Inspecting Candidate 2...")
        elif c_mac > 0:
            target_xpath = new_xpath_mac
            print("Inspecting MAC Selector...")
        
        if target_xpath:
            containers = page.locator(target_xpath)
            count = await containers.count()
            
            for i in range(count):
                print(f"\n  Container {i}:")
                cont = containers.nth(i)
                
                # Try Label (Preceding Sibling Span)
                try:
                    label_handle = cont.locator("xpath=preceding-sibling::span").first
                    if await label_handle.count() > 0:
                        label = await label_handle.text_content()
                        print(f"    Label (Sibling): '{label.strip()}'")
                    else:
                        print("    Label (Sibling): [Not Found]")
                except: pass
                
                # Content Inspection
                try:
                    txt = await cont.text_content()
                    print(f"    Text Content: {txt.strip()[:100]}...")
                    
                    btns = cont.locator("button")
                    b_count = await btns.count()
                    print(f"    Buttons: {b_count}")
                    if b_count > 0:
                        b_txt = await btns.first.text_content()
                        print(f"    First Button: {b_txt.strip()}")
                except Exception as e:
                    print(f"    Error inspecting content: {e}")

        # 5. SEMANTIC LABEL DISCOVERY
        print("\n🔍 Semantic Label Discovery:")
        labels_to_find = ["Màu sắc", "Màu", "Dung lượng", "Kích thước màn hình"]
        
        for lbl in labels_to_find:
             print(f"  Searching for label: '{lbl}'...")
             candidates = page.locator(f"text={lbl}")
             count = await candidates.count()
             print(f"    Found {count} candidates.")
             
             for i in range(min(count, 5)): # Check first 5
                 cand = candidates.nth(i)
                 if await cand.is_visible():
                     print(f"    Candidate {i} (Visible):")
                     # Print Tag Name
                     tag = await cand.evaluate("el => el.tagName")
                     print(f"      Tag: {tag}")
                     # Print Outer HTML
                     html = await cand.evaluate("el => el.outerHTML")
                     print(f"      HTML: {html[:100]}...")
                     
                     # Print Parent HTML
                     parent = cand.locator("..")
                     p_html = await parent.evaluate("el => el.outerHTML")
                     print(f"      Parent: {p_html[:200]}...")
                     
                     # Check next sibling
                     sibling = cand.locator("xpath=following-sibling::div")
                     if await sibling.count() > 0:
                         print("      Has following-sibling::div matching container pattern?")
                         s_html = await sibling.first.evaluate("el => el.outerHTML")
                         print(f"      Sibling HTML: {s_html[:200]}...")
        # 6. PAGE HEALTH CHECK
        print("\n🔍 Page Health Check:")
        try:
             # Check H1
             h1 = page.locator("h1").first
             if await h1.count() > 0:
                 txt = await h1.text_content()
                 print(f"  H1 Title: {txt.strip()}")
             else:
                 print("  H1 Title: [Not Found]")
                 
             # Check Price
             price = page.locator(".price, .product-price, #price-product").first
             if await price.count() > 0:
                 p_txt = await price.text_content()
                 print(f"  Price: {p_txt.strip()}")
             else:
                 print("  Price: [Not Found]")
                 
             # Check Buy Button
             buy_btn = page.locator("text=MUA NGAY, text=Trả góp").first
             if await buy_btn.count() > 0:
                 print("  Buy Button: Found")
             else:
                 print("  Buy Button: [Not Found]")
        except Exception as e:
            print(f"  Health Check Error: {e}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
