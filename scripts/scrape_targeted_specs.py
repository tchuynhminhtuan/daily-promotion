
import asyncio
import sqlite3
from playwright.async_api import async_playwright

DB_PATH = "catalog/price_history.db"

# The specific URL user provided that reveals M3/M5 models
TARGET_URL = "https://www.apple.com/ipad/compare/?modelList=ipad-pro-11-m5,ipad-air-11-m3,ipad-air-13-m3"

async def scrape_targeted():
    print(f"🚀 Launching Targeted Scraper: {TARGET_URL}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(TARGET_URL)
        await page.wait_for_load_state('networkidle')
        
        # Apple Compare Table Structure
        # .rf-compare-cell are the columns.
        # We need to map column index to product name.
        
        # 1. Get Product Names
        # Selector usually: .rf-compare-header-productname or h3.typography-label
        titles = await page.locator(".rf-product-overview-name").all_text_contents()
        print(f"Found products: {titles}")
        
        specs_map = {} # { "iPad Pro M5": { "chip": "...", "display": "..." } }
        
        # Initialize map
        for t in titles:
            clean_t = t.replace("\n", " ").strip()
            specs_map[clean_t] = {}
            
        # 2. Extract Specs
        # This is tricky because the table rows map to columns.
        # We'll look for specific sections.
        
        # Helper to get text for a row
        async def get_row_text(section_class, row_label=None):
            # This logic depends on Apple's DOM. 
            # Simplified: Grab the 'Chip' section text for each column.
            pass
        
        # Improved Strategy:
        # Evaluate JS to return structured data
        data = await page.evaluate('''() => {
            const products = Array.from(document.querySelectorAll('.rf-product-overview-name')).map(e => e.innerText.trim());
            
            // Helper to get text from a cell
            const getCells = (selector) => {
                return Array.from(document.querySelectorAll(selector)).map(e => e.innerText.trim().replace(/\\n/g, " "));
            };
            
            const chips = getCells('.rf-cpu-name, .rf-digitalmat-copy, .rf-tech-specs-chip'); 
            // Note: Selectors vary. rf-product-overview-chip usually exists
            
            // Try to find the Chip row
            // Apple Compare uses .rf-compare-cell for everything.
            // We rely on order. 
            
            return {
                products: products,
                chips: Array.from(document.querySelectorAll('.rf-product-overview-chip')).map(e => e.innerText.trim()),
                displays: Array.from(document.querySelectorAll('.rf-product-overview-display')).map(e => e.innerText.trim()),
                cameras: Array.from(document.querySelectorAll('.rf-product-overview-camera')).map(e => e.innerText.trim())
            };
        }''')
        
        print("Raw Data:", data)
        
        # Database Update
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        mapping = {
            "iPad Pro 11-inch (M5)": "ipad_pro_m5", # Need to match DB keys
            "iPad Pro 11‑in. (M5)": "ipad_pro_m5",
            "iPad Air 11-inch (M3)": "ipad_air_m3",
            "iPad Air 11‑in. (M3)": "ipad_air_m3",
            "iPad Air 13-inch (M3)": "ipad_air_m3", # Mapping 13" to same key for now? Or do we have ipad_air_13_m3?
            "iPad Air 13‑in. (M3)": "ipad_air_m3"
        }
        
        for i, prod_name in enumerate(data['products']):
            # Normalize name
            db_key = None
            for k, v in mapping.items():
                if k in prod_name:
                    db_key = v
                    break
            
            if not db_key:
                # Try simple fuzzy
                if "M5" in prod_name: db_key = "ipad_pro_m5"
                elif "M3" in prod_name and "Air" in prod_name: db_key = "ipad_air_m3"
            
            if db_key:
                chip = data['chips'][i] if i < len(data['chips']) else None
                display = data['displays'][i] if i < len(data['displays']) else None
                camera = data['cameras'][i] if i < len(data['cameras']) else None
                
                print(f"Updating {db_key}: Chip={chip}, Display={display}")
                
                # Get Product ID
                cursor.execute("SELECT id FROM products WHERE key = ?", (db_key,))
                res = cursor.fetchone()
                if res:
                    pid = res[0]
                    cursor.execute("""
                        UPDATE specs 
                        SET chip = ?, display = ?, back_camera = ? 
                        WHERE product_id = ?
                    """, (chip, display, camera, pid))
                    if cursor.rowcount == 0:
                        # Insert if missing
                        cursor.execute("""
                            INSERT INTO specs (product_id, chip, display, back_camera)
                            VALUES (?, ?, ?, ?)
                        """, (pid, chip, display, camera))
                        
        conn.commit()
        conn.close()
        print("✅ Database updated with scraped specs.")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_targeted())
