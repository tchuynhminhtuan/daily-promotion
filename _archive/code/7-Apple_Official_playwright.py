import asyncio
import json
import logging
from playwright.async_api import async_playwright, Page

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

TARGETS = {
    "iPhone": {
        "url": "https://www.apple.com/vn/shop/buy-iphone",
        "sub_page_selector": "a[href*='/vn/shop/buy-iphone/']", # Generic look for sub-links
        "selectors": {
            "title": "h1",
            "color": "input[name='dimensionColor'] + label",
            "storage": "input[name='dimensionCapacity'] + label"
        }
    },
    "iPad": {
        "url": "https://www.apple.com/vn/shop/buy-ipad",
        "sub_page_selector": "a[href*='/vn/shop/buy-ipad/']",
        "selectors": {
            "title": "h1",
            "color": "input[name='dimensionColor'] + label",
            "storage": "input[name='dimensionCapacity'] + label"
        }
    },
    "Mac": {
        "url": "https://www.apple.com/vn/shop/buy-mac",
        "sub_page_selector": "a[href*='/vn/shop/buy-mac/']",
        "selectors": {
            "title": "h1",
            "color": "input[name='chassis-dimensionColor'] + label",
            "storage": "input[name='dimensionHardDrive'] + label, input[name='chassis-dimensionHardDrive'] + label",
            "size": "input[name='chassis-dimensionScreensize'] + label"
        }
    },
    "Watch": {
        "url": "https://www.apple.com/vn/shop/buy-watch",
        "sub_page_selector": "a[href*='/vn/shop/buy-watch/']",
        "selectors": {
            "title": "h1",
            "color": "input[name='watch_cases-dimensionCaseMaterial'] + label",
            "size": "input[name='watch_cases-dimensionCaseSize'] + label"
        }
    }
}

async def get_product_links(page: Page, category_url: str):
    logging.info(f"Discovering links on {category_url}...")
    try:
        await page.goto(category_url, timeout=60000)
        await page.wait_for_load_state("networkidle")
        
        # Specific strategy: Look for "card-link" or links inside "shelf" elements.
        # Apple's structure usually lists families. 
        # For simplicity, we grab all hrefs that match the pattern AND look like product pages (not accessories).
        
        links = []
        hrefs = await page.evaluate(r"""
            () => {
                return Array.from(document.querySelectorAll('a')).map(a => a.href)
            }
        """)
        
        # Filter logic
        base_cat = category_url.split('/')[-1] # e.g. buy-iphone
        
        unique_links = set()
        for href in hrefs:
            if base_cat in href and href != category_url:
                # Exclude obvious non-product links if possible (accessories often stay in same dir?)
                # We'll rely on the scraper to fail gracefully for accessories or check title
                if "accessory" not in href:
                    unique_links.add(href)
        
        return list(unique_links)

    except Exception as e:
        logging.error(f"Error discovering links: {e}")
        return []

async def scrape_product_page(page: Page, category: str, url: str, selectors: dict):
    logging.info(f"Navigating to {url}...")
    try:
        await page.goto(url, timeout=60000)
        # Attempt to wait for a key element to ensure it's a product page
        try:
             await page.wait_for_selector(selectors['title'], timeout=5000)
        except:
             logging.info(f"Skipping {url} - likely not a product configurator page.")
             return None

    except Exception as e:
        logging.error(f"Failed to load {url}: {e}")
        return None

    # Extract Title
    title = "Unknown"
    try:
        h1_el = await page.query_selector(selectors['title'])
        if h1_el:
            title = await h1_el.inner_text()
            # Clean title
            title = title.replace("Mua ", "").strip()
    except Exception as e:
        logging.warning(f"Could not find title with selector {selectors['title']}: {e}")

    # Extract Colors
    colors = []
    try:
        # Check standard and chassis prefixed
        if 'color' in selectors:
             # Try provided selector
             color_labels = await page.query_selector_all(selectors['color'])
             if not color_labels:
                 # Fallback for Mac/Watch if prefix is missing in config
                 pass
             
             for label in color_labels:
                text = await label.inner_text()
                if text:
                     clean_text = text.split('\n')[0].strip()
                     colors.append(clean_text)
    except Exception as e:
        logging.warning(f"Error scraping colors on {url}: {e}")
    
    # Extract Storage / Size
    storage = []
    storage_selector = selectors.get('storage')
    if storage_selector:
         try:
             # handle comma separated selectors in logic if needed, but query_selector_all takes it
            storage_labels = await page.query_selector_all(storage_selector)
            for label in storage_labels:
                text = await label.inner_text()
                if text:
                    clean_text = text.split('\n')[0].strip()
                    storage.append(clean_text)
         except Exception as e:
             logging.warning(f"Error scraping storage on {url}: {e}")

    sizes = []
    size_selector = selectors.get('size')
    if size_selector:
        try:
             size_labels = await page.query_selector_all(size_selector)
             for label in size_labels:
                text = await label.inner_text()
                if text:
                    clean_text = text.split('\n')[0].strip()
                    sizes.append(clean_text)
        except:
            pass

    # Validation: If no "buy" options found, maybe it's not a buy page
    if not colors and not storage and not sizes:
        logging.info(f"No configured options found on {url}. Skipping.")
        return None

    return {
        "category": category,
        "url": url,
        "name": title,
        "colors": list(set(colors)),
        "storage": list(set(storage)),
        "sizes": list(set(sizes))
    }

async def main():
    results = {}
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        for category, data in TARGETS.items():
            results[category] = []
            selectors = data['selectors']
            
            # Dynamic discovery
            links = await get_product_links(page, data['url'])
            logging.info(f"Found {len(links)} potential links for {category}")
            
            for url in links:
                product_data = await scrape_product_page(page, category, url, selectors)
                if product_data:
                    results[category].append(product_data)
                    logging.info(f"Scraped {product_data['name']}: {len(product_data['colors'])} colors.")

        await browser.close()

    # Output to JSON
    with open('apple_official_catalog.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logging.info("Scraping completed. Data saved to apple_official_catalog.json")

if __name__ == "__main__":
    asyncio.run(main())
