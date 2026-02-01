from playwright.sync_api import sync_playwright

URL = "https://cellphones.com.vn/catalogsearch/result?q=marshall"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    print(f"Loading {URL}...")
    page.goto(URL, timeout=60000, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    
    selector = "//div[contains(@class, 'product-info')] | //div[contains(@class, 'item-product')] | //div[contains(@class, 'product-item')] | //a[contains(@class, 'product__link')]"
    containers = page.locator(selector)
    count = containers.count()
    print(f"Found {count} containers with selector: {selector}")
    
    for i in range(min(10, count)):
        container = containers.nth(i)
        tag = container.evaluate("el => el.tagName")
        cls = container.get_attribute("class")
        href = container.get_attribute("href")
        print(f"\n--- Container {i} ---")
        print(f"Tag: {tag}")
        print(f"Class: {cls}")
        print(f"Href: {href}")
        
        # Check sub-links
        sub_links = container.locator("a")
        sub_count = sub_links.count()
        print(f"Sub-links count: {sub_count}")
        if sub_count > 0:
            print(f"First sub-link href: {sub_links.first.get_attribute('href')}")
            
        # Check exclusion
        exclusion_xpath = ".//p[contains(@class, 'notification') and contains(@class, 'is-danger')]"
        excl_count = container.locator(exclusion_xpath).count()
        print(f"Exclusion element count: {excl_count}")
        
    browser.close()
