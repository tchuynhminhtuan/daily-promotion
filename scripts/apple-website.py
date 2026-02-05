import asyncio
import os
import sys
import re
import json
from datetime import datetime
import pytz
from playwright.async_api import Page
# Add current directory to sys.path so utils imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


total_links = ["https://support.apple.com/vi-vn/docs/iphone"]

async def main():
    async with asynccontextmanager(playwright.start)() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto("https://support.apple.com/vi-vn/docs/iphone")
        await page.wait_for_timeout(10000)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
