"""
Apple Compare Web Scraper
Scrapes rich specifications from Apple Vietnam Compare pages.
Iterates through all models in the dropdown and saves them as JSON.
"""
import asyncio
import json
import os
import argparse
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright

# Config
BASE_DIR = Path("catalog/specs")
CATEGORIES = {
    "iphone": "https://www.apple.com/vn/iphone/compare/",
    "ipad": "https://www.apple.com/vn/ipad/compare/",
    "mac": "https://www.apple.com/vn/mac/compare/",
    "watch": "https://www.apple.com/vn/watch/compare/",
    "airpods": "https://www.apple.com/vn/airpods/compare/"
}

async def scrape_category(category, url):
    print(f"\n🚀 Launching Scraper for: {category.upper()} ({url})")
    
    # Output Dir
    output_dir = BASE_DIR / category
    output_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        # Launch Browser
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print(f"🔗 Navigating to {url}...")
        await page.goto(url)
        await page.wait_for_load_state('networkidle')
        
        # 1. Discover Models
        print("🔍 Discovering models...")
        # Different selectors might exist for different categories, but usually selector-0 is consistent
        # AirPods page might differ slightly, let's verify logic or handle generically
        
        try:
            options = await page.evaluate('''() => {
                const select = document.getElementById('selector-0');
                if (!select) return [];
                return Array.from(select.options).map(o => ({
                    value: o.value,
                    text: o.text.trim()
                })).filter(o => o.value !== "summary" && o.value !== "");
            }''')
        except Exception as e:
            print(f"⚠️ Error finding selector-0: {e}")
            options = []

        if not options:
            print(f"⚠️ No dropdown found for {category}, trying alternate detection (AirPods might be static grid)...")
            # Some pages like AirPods might just list everything without a dropdown?
            # Actually AirPods compare page usually shows all models or has a picker.
            # Let's check if there are already columns.
            pass

        print(f"📋 Found {len(options)} models")

        if len(options) == 0:
            print("   ⚠️ No models found to cycle through. Converting visible page to single capture if possible?")
            # For now, just skip if empty (or maybe AirPods works differently)
            # await browser.close()
            # return

        # 2. Process in Chunks of 3 (Apple Compare limit)
        chunk_size = 3
        
        # If no options, maybe it's a fixed page (AirPods sometimes is). 
        # But for now assuming standard compare behavior.
        
        # Determine loop range
        loop_items = options if options else [{'value': 'default', 'text': 'Default View'}]
        
        # If options is empty but we want to scrape static content:
        if not options:
            # Just scrape what's there
            loop_items = []
            # Logic below depends on cycling options. If static, we need different logic.
            # Let's assume standard behavior for now as per original script.

        for i in range(0, len(options), chunk_size):
            chunk = options[i:i+chunk_size]
            global_indices = [i + j for j in range(len(chunk))]
            chunks_values = [m['value'] for m in chunk]

            print(f"\n🔄 Processing Chunk {i//chunk_size + 1}: {[m['text'] for m in chunk]}")
            
            # Select Models in Slots 0, 1, 2
            for idx, model in enumerate(chunk):
                selector_id = f"selector-{idx}"
                try:
                    # Check if selector exists first
                    if await page.query_selector(f"#{selector_id}"):
                        await page.select_option(f"#{selector_id}", model['value'])
                    else:
                        print(f"   ⚠️ Selector #{selector_id} not found")
                except Exception as e:
                    print(f"   ⚠️ Failed to select {model['text']} in #{selector_id}: {e}")
            
            # Wait for content update
            print(f"   ⏳ Waiting for data to load...")
            await page.wait_for_timeout(2500) 
            
            # 3. Scrape Data Row-by-Row (HYBRID STRATEGY)
            column_data = await page.evaluate('''({ chunk_len, global_indices, chunks_values }) => {
                const results = [];
                for(let i=0; i<chunk_len; i++) results.push({});
                
                // Helper to get image from style
                const getBgImg = (el) => {
                     if(!el) return null;
                     const bg = window.getComputedStyle(el).backgroundImage;
                     const match = bg && bg.match(/url\\(['"]?(.*?)['"]?\\)/);
                     return (match && match[1]) ? match[1] : null;
                };

                // HERO IMAGES
                const galleryRow = document.querySelector('.row-gallery') || document.querySelector('.compare-row.gallery');
                if (galleryRow) {
                    const imgDivs = galleryRow.querySelectorAll('.compare-column');
                    imgDivs.forEach((div, idx) => {
                        if (idx < chunk_len) {
                            const img = div.querySelector('img');
                            if (img && img.src) results[idx]['hero_image'] = img.src;
                            else results[idx]['hero_image'] = getBgImg(div.querySelector('.gallery-image') || div);
                        }
                    });
                }

                // DATA ROWS
                const rows = document.querySelectorAll('.compare-row, .backport-row, .tech-specs-row, .row');
                let lastHeader = "General";
                
                rows.forEach(row => {
                    // Row Visibility Check
                    const rowStyle = window.getComputedStyle(row);
                    if (rowStyle.display === 'none' || rowStyle.visibility === 'hidden') return;

                    // Header
                    const hEl = row.querySelector('.compare-rowheader, .row-header, .column-label');
                    let headerText = hEl ? hEl.innerText.trim() : "";
                    
                    // Blacklist Garbage Rows
                    const blacklist = ["Dropdown", "Buy", "Price-Sticky", "Tech Specs", "All iPhone models", "Shop", "Learn more", "AR Quick Look"];
                    if (blacklist.some(b => headerText.includes(b))) return;
                    
                    if (headerText) {
                        lastHeader = headerText;
                    } else {
                        // Inherit from previous section if no header (e.g. camera specs rows)
                        headerText = lastHeader;
                    }

                    // Skip if we still don't have a header (very top of table?)
                    if (!headerText) return;

                    const key = headerText;
                    
                    const cells = row.querySelectorAll('.compare-column');
                    
                    // Logic to map cells to results
                    // Dynamic vs Static grid check is tricky.
                    // Simplified: Just take the first N cells matching our chunk_len
                    
                    for (let localIdx = 0; localIdx < chunk_len; localIdx++) {
                         let targetCell = null;
                         
                         // Try simple mapping first
                         if (localIdx < cells.length) {
                             targetCell = cells[localIdx];
                         }

                         if (targetCell) {
                             const cStyle = window.getComputedStyle(targetCell);
                             
                             if (cStyle.display !== 'none' && cStyle.visibility !== 'hidden') {
                                 const clone = targetCell.cloneNode(true);
                                 clone.querySelectorAll('.footnote, sup, .visuallyhidden').forEach(e => e.remove());
                                 
                                 // Clean Garbage UI Text in content
                                 const garbageText = ["Image Link", "View in AR", "Available at authorized resellers", "New", "Mới"];
                                 
                                 let text = "";
                                 const listItems = clone.querySelectorAll('li, .cell-item');
                                 if (listItems.length > 0) {
                                     text = Array.from(listItems)
                                         .map(li => li.innerText.trim())
                                         .filter(t => t && !garbageText.includes(t)) // Filter garbage lines
                                         .join("\\n");
                                 } else {
                                     text = clone.innerText.trim();
                                     if (!text) {
                                         const img = clone.querySelector('img');
                                         if (img) text = img.alt || "";
                                     }
                                     // Filter garbage single text
                                     if (garbageText.includes(text)) text = "";
                                 }
                                 
                                 if (text) {
                                     if (!results[localIdx][key]) results[localIdx][key] = [];
                                     results[localIdx][key].push(...text.split('\\n'));
                                 }
                             }
                         }
                    }
                });
                
                return results;
            }''', {'chunk_len': len(chunk), 'global_indices': global_indices, 'chunks_values': chunks_values})
            
            # Save Files
            for idx, data in enumerate(column_data):
                model = chunk[idx]
                final_json = {
                    "device_name": model['text'],
                    "model_key": model['value'],
                    "_category": category,
                    "_adapter_version": "3.3_daily_promo",
                    "_scraped_at": datetime.now().isoformat(),
                    **data
                }
                
                safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', model['text'])
                filename = f"{safe_name}.json"
                filepath = output_dir / filename
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(final_json, f, ensure_ascii=False, indent=2)
                print(f"   ✅ Saved {filename}")

        await browser.close()
    print(f"\n🎉 {category.upper()} Scraping Complete!")

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", type=str, default="all", help="iphone, ipad, mac, watch, airpods, or all")
    args = parser.parse_args()
    
    target_cats = []
    if args.category == "all":
        target_cats = list(CATEGORIES.keys())
    elif args.category in CATEGORIES:
        target_cats = [args.category]
    else:
        print(f"❌ Unknown category: {args.category}")
        return

    # Install playwright browsers if needed? 
    # Usually handled by environment.
    
    for cat in target_cats:
        await scrape_category(cat, CATEGORIES[cat])

if __name__ == "__main__":
    import re
    asyncio.run(main())
