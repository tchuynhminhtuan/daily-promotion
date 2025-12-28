from playwright.sync_api import sync_playwright

URL = "https://cellphones.com.vn/iphone-13.html"

# Current Selectors
CURRENT_COLOR = ".button__change-color"
CURRENT_STORAGE = "a.item-linked"

# User Suggested Selectors
USER_COLOR = "//ul[contains(@class, 'list-variants')]/li"
USER_STORAGE = "//div[contains(@class, 'list-linked')]/a"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    print(f"Loading {URL}...")
    page.goto(URL, timeout=60000, wait_until="domcontentloaded")
    
    # 1. Check Colors
    c_curr = page.locator(CURRENT_COLOR).count()
    c_user = page.locator(USER_COLOR).count()
    print(f"Colors (Current: {CURRENT_COLOR}): {c_curr}")
    print(f"Colors (User: {USER_COLOR}): {c_user}")
    
    # 2. Check Storage
    s_curr = page.locator(CURRENT_STORAGE).count()
    s_user = page.locator(USER_STORAGE).count()
    print(f"Storage (Current: {CURRENT_STORAGE}): {s_curr}")
    print(f"Storage (User: {USER_STORAGE}): {s_user}")
    
    browser.close()
