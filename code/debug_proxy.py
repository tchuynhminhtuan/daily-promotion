import asyncio
import os
from playwright.async_api import async_playwright

async def main():
    print("🔍 DEBUG: Starting Proxy Connectivity Test...")
    
    proxy_server = os.environ.get("PROXY_SERVER", "").strip()
    if not proxy_server:
        print("❌ DEBUG: No PROXY_SERVER found.")
        return

    # 1. Parse Proxy Logic (Same as scraper)
    if proxy_server:
        parts = proxy_server.split(':')
        if len(parts) == 4 and "@" not in proxy_server and not proxy_server.startswith("http"):
            ip, port, user, pw = parts
            proxy_server = f"http://{user}:{pw}@{ip}:{port}"
            print("⚠️ DEBUG: Reformatted IP:PORT:USER:PASS string.")
        
        if not proxy_server.startswith("http"):
            proxy_server = f"http://{proxy_server}"

    print(f"ℹ️ DEBUG: Proxy Server: {proxy_server.split('@')[-1] if '@' in proxy_server else '***'}") # Mask credentials

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(
                headless=True,
                proxy={"server": proxy_server}
            )
            page = await browser.new_page()
            
            print("⏳ DEBUG: Attempting to connect to http://example.com ...")
            start_time = asyncio.get_event_loop().time()
            
            response = await page.goto("http://example.com", timeout=30000)
            
            end_time = asyncio.get_event_loop().time()
            print(f"✅ DEBUG: Connection Successful! Status: {response.status}")
            print(f"⏱️ DEBUG: Time taken: {end_time - start_time:.2f} seconds")
            
            await browser.close()
        except Exception as e:
            print(f"❌ DEBUG: Connection FAILED: {e}")
            exit(1)

if __name__ == "__main__":
    asyncio.run(main())
