import asyncio
from playwright.async_api import async_playwright

URL = "https://fptshop.com.vn/dien-thoai/iphone-13"

# Selectors from the original script
OTHER_PROMO_SELECTOR = "(//div[contains(@class, 'flex flex-col overflow-hidden bg-white')])[1]"
OTHER_PROMO_BTN_SELECTOR = "(//div[contains(@class, 'flex flex-col overflow-hidden bg-white')])[1]/div/button"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        print(f"Navigating to {URL}")
        await page.goto(URL, timeout=60000)
        await page.wait_for_timeout(5000)

        # Check for popup
        try:
            de_sau_btn = page.locator("button").filter(has_text="Để sau")
            if await de_sau_btn.count() > 0 and await de_sau_btn.is_visible():
                print("Found 'Để sau' popup, clicking...")
                await de_sau_btn.click()
                await page.wait_for_timeout(1000)
        except Exception as e:
            print(f"Popup error: {e}")

        print("\n--- BEFORE CLICK ---")
        content_before = await page.locator(OTHER_PROMO_SELECTOR).inner_text()
        print(content_before)

        print("\n--- ATTEMPTING CLICK ---")
        btn = page.locator(OTHER_PROMO_BTN_SELECTOR).first
        if await btn.count() > 0 and await btn.is_visible():
            print("Button found and visible. Clicking...")
            await btn.click()
            await page.wait_for_timeout(2000)
        else:
            print("Button NOT found or NOT visible.")

        print("\n--- AFTER CLICK ---")
        content_after = await page.locator(OTHER_PROMO_SELECTOR).inner_text()
        content_after = content_after.replace("Xem chi tiết", "\n").replace("Thu gọn", "").strip()
        print(content_after)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
