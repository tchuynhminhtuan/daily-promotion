
import asyncio
import os
import sys
import json
import csv
from datetime import datetime
import pytz

# Mock import since we can't install crawl4ai in this env,
# but this code is written to be runnable if the user installs it.
# pip install crawl4ai
try:
    from crawl4ai import AsyncWebCrawler
    from crawl4ai.extraction_strategy import JsonCssExtractionStrategy, LLMExtractionStrategy
except ImportError:
    print("❌ Crawl4AI not installed. Please run: pip install crawl4ai")
    sys.exit(1)

# Add utils path for site list
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/src")
try:
    from crawlers.utils.sites import total_links
except ImportError:
    # Fallback URLs if import fails
    total_links = {"fpt_urls": [
        "https://fptshop.com.vn/dien-thoai/iphone-16-pro-max",
        "https://fptshop.com.vn/dien-thoai/iphone-16",
        "https://fptshop.com.vn/dien-thoai/iphone-15-pro-max"
    ]}

class FPTCrawl4AI:
    def __init__(self):
        self.local_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        self.date_str = datetime.now(self.local_tz).strftime('%Y-%m-%d')
        self.output_dir = f"data/raw/{self.date_str}"
        os.makedirs(self.output_dir, exist_ok=True)
        self.csv_path = f"{self.output_dir}/1-fpt-crawl4ai-{self.date_str}.csv"
        
        # Define Schema for JSON CSS Extraction
        # This replaces lines 20-42 in the old file
        self.schema = {
            "name": "FPT Product Extraction",
            "baseSelector": "body", 
            "fields": [
                {
                    "name": "Product_Name",
                    "selector": "h1.text-textOnWhitePrimary",
                    "type": "text",
                },
                {
                    "name": "Gia_Khuyen_Mai",
                    "selector": "#price-product .h4-bold",
                    "type": "text",
                },
                {
                    "name": "Gia_Niem_Yet",
                    "selector": "#price-product .line-through",
                    "type": "text",
                },
                {
                    "name": "Khuyen_Mai_Html", 
                    "selector": "div.mt-2.flex.flex-col.gap-2", # Original Selector
                    "type": "html" # Capture HTML to be safe, or text
                }
            ]
        }

    def init_csv(self):
        with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(["Product_Name", "Gia_Khuyen_Mai", "Gia_Niem_Yet", "Khuyen_Mai_Raw", "Link"])

    async def process_url(self, crawler, url):
        print(f"🕷️ Crawling: {url}")
        
        # 1. Extraction Strategy (CSS for speed)
        extraction_strategy = JsonCssExtractionStrategy(self.schema)

        # 2. Run Crawler
        # magic=True enables anti-bot protections automatically (like browser-use)
        result = await crawler.arun(
            url=url,
            extraction_strategy=extraction_strategy,
            magic=True, 
            bypass_cache=True
        )

        if not result.success:
            print(f"❌ Failed: {url} - {result.error_message}")
            return

        # 3. Parse JSON Result
        data = json.loads(result.extracted_content)
        
        # Some cleanup logic (ported from old scraper)
        if data:
            item = data[0] # Usually returns list
            
            p_name = item.get("Product_Name", "").strip()
            price_sale = item.get("Gia_Khuyen_Mai", "").replace("₫", "").replace(".", "").strip()
            price_list = item.get("Gia_Niem_Yet", "").replace("₫", "").replace(".", "").strip()
            promo_raw = item.get("Khuyen_Mai_Html", "").strip()
            
            # Save to CSV
            with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow([p_name, price_sale, price_list, promo_raw, url])
            
            print(f"✅ Saved: {p_name} | Price: {price_sale}")
        else:
            print(f"⚠️ No data extracted for {url}")

    async def run(self):
        self.init_csv()
        urls = total_links.get('fpt_urls', [])[:5] # Test with 5 URLs
        
        async with AsyncWebCrawler(verbose=True) as crawler:
            for url in urls:
                await self.process_url(crawler, url)

if __name__ == "__main__":
    scraper = FPTCrawl4AI()
    asyncio.run(scraper.run())
