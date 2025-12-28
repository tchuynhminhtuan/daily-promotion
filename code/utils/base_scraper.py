import asyncio
import csv
import os
import sys
import re
from datetime import datetime
import pytz
from playwright.async_api import async_playwright, Page

# Add the parent directory to sys.path to ensure imports work if run from different locations
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class BaseScraper:
    def __init__(self, urls, headless=True, max_concurrent=8):
        self.urls = urls
        self.headless = headless
        self.max_concurrent = max_concurrent

        # Default config, can be overridden by child classes or env vars
        self.take_screenshot = os.environ.get("TAKE_SCREENSHOT", "False").lower() == "true"
        self.block_images = os.environ.get("BLOCK_IMAGES", "True").lower() == "true"
        self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

        # Setup paths
        self.current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # Allow override for sub-projects (like Marshall) to avoid overwriting main data
        env_output_path = os.environ.get("BASE_OUTPUT_PATH")
        if env_output_path:
            self.base_output_path = os.path.abspath(env_output_path)
        else:
            self.base_output_path = os.path.join(self.current_dir, '../content')
        self.local_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        self.date_str = datetime.now(self.local_tz).strftime('%Y-%m-%d')

        # CSV setup
        self.csv_path = self.setup_csv()
        self.csv_lock = asyncio.Lock()

    def get_filename_prefix(self):
        """Override this in child class. E.g. '1-fpt'"""
        raise NotImplementedError

    def get_fieldnames(self):
        """Override this to define CSV columns."""
        return [
            "Product_Name", "Color", "Ton_Kho", "Gia_Niem_Yet", "Gia_Khuyen_Mai",
            "Date", "Khuyen_Mai", "Thanh_Toan", "Link", "screenshot_name"
        ]

    def setup_csv(self):
        output_dir = os.path.join(self.base_output_path, self.date_str)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        prefix = self.get_filename_prefix()
        # Append _test if in test mode
        suffix = "_test" if os.environ.get("TEST_MODE") == "True" else ""
        file_path = os.path.join(output_dir, f"{prefix}-{self.date_str}{suffix}.csv")

        # Create image directory based on prefix
        # Convention: if prefix is '1-fpt', img dir is 'img_fpt'
        # Split by '-' and take the last part or custom logic?
        # Looking at existing: 1-fpt -> img_fpt, 2-mw -> img_mw
        # So we can derive it.
        site_code = prefix.split('-')[-1] if '-' in prefix else prefix
        img_dir = os.path.join(output_dir, f'img_{site_code}')
        os.makedirs(img_dir, exist_ok=True)
        self.img_dir = img_dir # Store for later use

        # Overwrite if exists
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass

        with open(file_path, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=self.get_fieldnames(), delimiter=";")
            writer.writeheader()
        return file_path

    async def write_to_csv(self, data):
        async with self.csv_lock:
            with open(self.csv_path, "a", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=self.get_fieldnames(), delimiter=";")
                writer.writerow(data)

    async def get_text_safe(self, page, selector, timeout=1000):
        try:
            if not selector: return ""
            if await page.locator(selector).count() > 0:
                # Try innerText first, fallback to textContent
                try:
                    return await page.locator(selector).first.inner_text(timeout=timeout)
                except:
                     return await page.locator(selector).first.text_content(timeout=timeout)
        except: pass
        return ""

    async def get_element_text_with_fallbacks(self, page, selectors: list, timeout=1000) -> str:
        """
        Iterates through a list of selectors/XPaths.
        Returns the first non-empty text found.
        """
        if not selectors:
            return ""

        for selector in selectors:
            try:
                text = await self.get_text_safe(page, selector, timeout)
                if text and text.strip():
                    return text.strip()
            except:
                continue
        return ""

    def extract_price(self, text: str) -> int:
        """
        Standardizes price cleaning.
        Removes non-digit characters.
        Handles 'Price on request' or empty strings by returning 0.
        """
        if not text:
            return 0

        # Check for "Price on request" patterns (Vietnamese)
        text_lower = text.lower()
        if "liên hệ" in text_lower or "price on request" in text_lower:
            return 0

        # Remove non-digits
        clean = re.sub(r'[^\d]', '', text)
        return int(clean) if clean else 0

    async def remove_overlays(self, page):
        """Common overlay removal, can be extended by child."""
        try:
            await page.evaluate("""() => {
                document.querySelectorAll('.popup-modal, .overlay, .loading-cover, .modal-backdrop').forEach(e => e.remove());
            }""")
        except: pass

    async def scrape(self, page: Page, url: str):
        """Abstract method to implement site-specific logic."""
        raise NotImplementedError

    async def _process_url_wrapper(self, semaphore, browser, url):
        async with semaphore:
            page = await browser.new_page(
                user_agent=self.user_agent,
                viewport={"width": 1920, "height": 1080},
                device_scale_factor=1,
                ignore_https_errors=True
            )

            if self.block_images:
                await page.route("**/*", lambda route: route.abort()
                    if route.request.resource_type in ["image", "media", "font"]
                    else route.continue_())

            try:
                print(f"Processing: {url}")
                # Common navigation with retry?
                try:
                    await page.goto(url, timeout=60000, wait_until="domcontentloaded")
                except Exception as e:
                    print(f"⚠️ Navigation failed: {url} - {e}")
                    # Child might want to handle retry or just return
                    return

                await self.scrape(page, url)

            except Exception as e:
                print(f"Error processing {url}: {e}")
            finally:
                await page.close()

    async def run(self):
        print(f"Starting {self.__class__.__name__} with {len(self.urls)} URLs.")
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async with async_playwright() as p:
            launch_options = {
                "headless": self.headless,
                "args": [
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--window-size=1920,1080",
                    "--ignore-certificate-errors"
                ],
                "ignore_default_args": ["--enable-automation"]
            }

            # Proxy handling - Check env var convention "ENABLE_PROXY_SITECODE"
            # We need to know the site code. E.g. FPT, MW.
            # We can use the prefix again.
            prefix = self.get_filename_prefix().upper()
            # prefix usually '1-fpt', so split
            site_key = prefix.split('-')[-1] if '-' in prefix else prefix
            # Handle special cases if any? 1-fpt -> FPT. 4-hoangha -> HOANGHA?
            # Let's verify env vars used in original files:
            # FPT -> ENABLE_PROXY_FPT
            # MW -> ENABLE_PROXY_MW
            # Viettel -> ENABLE_PROXY_VIETTEL
            # CPS -> ENABLE_PROXY_CPS
            # HoangHa -> ENABLE_PROXY_HOANGHA
            # DDV -> ENABLE_PROXY_DDV

            # Map common site codes
            proxy_env_key = f"ENABLE_PROXY_{site_key}"
            # Special case mapping if needed (e.g. if I use '1-fpt' -> 'FPT')

            proxy_server = os.environ.get("PROXY_SERVER", "").strip()
            if proxy_server and os.environ.get(proxy_env_key, "False").lower() == "true":
                 if not proxy_server.startswith("http"):
                    parts = proxy_server.split(':')
                    if len(parts) == 4 and "@" not in proxy_server:
                        ip, port, user, pw = parts
                        proxy_server = f"http://{user}:{pw}@{ip}:{port}"
                    else:
                        proxy_server = f"http://{proxy_server}"
                 print(f"🌐 Using Proxy ({site_key}): {proxy_server}")
                 launch_options["proxy"] = {"server": proxy_server}

            browser = await p.chromium.launch(**launch_options)

            tasks = [self._process_url_wrapper(semaphore, browser, url) for url in self.urls]
            await asyncio.gather(*tasks)

            await browser.close()

        print(f"Finished {self.__class__.__name__}.")
