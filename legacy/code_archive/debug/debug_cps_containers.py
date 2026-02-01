from playwright.sync_api import sync_playwright

URL = "https://cellphones.com.vn/catalogsearch/result?q=marshall"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    print(f"Loading {URL}...")
    page.goto(URL, timeout=60000, wait_until="domcontentloaded")
    
    # Wait for a bit
    page.wait_for_timeout(3000)
    
    containers = page.locator("//div[contains(@class, 'product-info')] | //div[contains(@class, 'item-product')] | //div[contains(@class, 'product-item')]")
    count = containers.count()
    print(f"Found {count} containers.")
    
    for i in range(min(5, count)):
        container = containers.nth(i)
        html = container.inner_html()
        print(f"\n--- Container {i} HTML ---")
        print(html[:1000]) # Print first 1000 chars
        print("------------------------")
        
    browser.close()
