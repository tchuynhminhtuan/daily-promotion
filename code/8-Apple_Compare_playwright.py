"""
Apple Compare Web Scraper (Ported from iPhone-Youtube project)
Scrapes rich specifications from https://www.apple.com/vn/ipad/compare/
Iterates through all models in the dropdown and saves them as JSON.
"""
import asyncio
import json
import os
import re
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Config
BASE_DIR = Path("/Users/brucehuynh/GitHub/daily-promotion/analysis/scraped_data/compare_specs")
CATEGORIES = {
    "iphone": "https://www.apple.com/vn/iphone/compare/",
    "watch": "https://www.apple.com/vn/watch/compare/",
    "ipad": "https://www.apple.com/vn/ipad/compare/",
    "mac": "https://www.apple.com/vn/mac/compare/",
}

async def scrape_category(category, url):
    logging.info(f"🚀 Launching Scraper for: {category.upper()} ({url})")
    
    output_dir = BASE_DIR / category
    output_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        # Launch Browser
        browser = await p.chromium.launch(headless=True)
        # Use a context with distinct locale if needed, but usually defaults are fine
        page = await browser.new_page()
        
        logging.info(f"🔗 Navigating to {url}...")
        try:
            await page.goto(url, timeout=60000)
            await page.wait_for_load_state('networkidle')
        except Exception as e:
            logging.error(f"Failed to load {url}: {e}")
            await browser.close()
            return

        # 1. Discover Models
        logging.info("🔍 Discovering models...")
        # Check if selector exists
        try:
             await page.wait_for_selector('#selector-0', timeout=10000)
        except:
             logging.error(f"Could not find model selector on {url}")
             await browser.close()
             return

        options = await page.evaluate('''() => {
            const select = document.getElementById('selector-0');
            return Array.from(select.options).map(o => ({
                value: o.value,
                text: o.text.trim()
            })).filter(o => o.value !== "summary" && o.value !== "");
        }''')
        logging.info(f"📋 Found {len(options)} models")

        # 2. Process in Chunks of 3 (Apple Compare limit)
        chunk_size = 3
        
        for i in range(0, len(options), chunk_size):
            chunk = options[i:i+chunk_size]
            
            # Global indices logic from original script
            global_indices = [i + j for j in range(len(chunk))]
            chunks_values = [m['value'] for m in chunk]

            logging.info(f"🔄 Processing Chunk {i//chunk_size + 1}: {[m['text'] for m in chunk]}")
            
            # Select Models in Slots 0, 1, 2
            for idx, model in enumerate(chunk):
                selector_id = f"selector-{idx}"
                try:
                    # Ensure selector is visible
                    await page.wait_for_selector(f"#{selector_id}")
                    await page.select_option(f"#{selector_id}", model['value'])
                except Exception as e:
                    logging.warning(f"   ⚠️ Failed to select {model['text']} in #{selector_id}: {e}")
            
            # Wait for content update
            logging.info(f"   ⏳ Waiting for data to load...")
            await page.wait_for_timeout(3000) 
            
            # 3. Scrape Data Row-by-Row (HYBRID STRATEGY from Legacy)
            # Embedding the complex scraper logic
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
                // Extended selector list based on new research + legacy
                const rows = document.querySelectorAll('.compare-row, .backport-row, .tech-specs-row, .row');
                let lastHeader = "General";
                
                rows.forEach(row => {
                    // Row Visibility Check
                    const rowStyle = window.getComputedStyle(row);
                    if (rowStyle.display === 'none' || rowStyle.visibility === 'hidden') return;

                    // Header
                    // Try to find header inside the row, or previous sibling
                    const hEl = row.querySelector('.compare-rowheader, .row-header, .column-label, h2, h3, h4');
                    let headerText = hEl ? hEl.innerText.trim() : "";
                    
                    // Blacklist Garbage Rows
                    const blacklist = ["Dropdown", "Buy", "Price-Sticky", "Tech Specs", "All iPhone models", "Shop", "Learn more", "AR Quick Look", "Tóm tắt", "Summary"];
                    if (blacklist.some(b => headerText.includes(b))) return;
                    
                    if (headerText) {
                        lastHeader = headerText;
                    } else {
                        headerText = lastHeader;
                    }

                    if (!headerText) return;

                    const key = headerText;
                    
                    const cells = row.querySelectorAll('.compare-column, .cell-item, div[role="cell"]'); 
                    // Note: .cell-item sometimes is inside .compare-column. 
                    // Better strategy: Select strict columns
                    const columns = row.querySelectorAll('.compare-column');
                    
                    if (columns.length === 0) return;

                    const isStaticGrid = columns.length > 5; // Heuristic from legacy

                    for (let localIdx = 0; localIdx < chunk_len; localIdx++) {
                         let targetCell = null;

                         if (isStaticGrid) {
                             // STATIC GRID Logic
                             const globalIdx = global_indices[localIdx];
                             const modelValue = chunks_values[localIdx];
                             
                             const elById = document.getElementById(modelValue);
                             if (elById && row.contains(elById)) {
                                 targetCell = elById;
                             } else {
                                 if (globalIdx < columns.length) {
                                     targetCell = columns[globalIdx];
                                 }
                             }
                         } else {
                             // DYNAMIC GRID Logic
                             if (localIdx < columns.length) {
                                  targetCell = columns[localIdx];
                             }
                         }

                         if (targetCell) {
                             const cStyle = window.getComputedStyle(targetCell);
                             
                             if (cStyle.display !== 'none' && cStyle.visibility !== 'hidden') {
                                 const clone = targetCell.cloneNode(true);
                                 clone.querySelectorAll('.footnote, sup, .visuallyhidden').forEach(e => e.remove());
                                 
                                 const garbageText = ["Image Link", "View in AR", "Available at authorized resellers", "New", "Mới"];
                                 
                                 let text = "";
                                 // Try to get structured lists
                                 const listItems = clone.querySelectorAll('li, .cell-item');
                                 if (listItems.length > 0) {
                                     text = Array.from(listItems)
                                         .map(li => li.innerText.trim())
                                         .filter(t => t && !garbageText.includes(t)) 
                                         .join("\\n");
                                 } else {
                                     text = clone.innerText.trim();
                                     if (!text) {
                                         const img = clone.querySelector('img');
                                         if (img) text = img.alt || "";
                                     }
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
                    "_scraped_at": datetime.now().isoformat(),
                    **data
                }
                
                safe_name = re.sub(r'[^\w\-_]', '_', model['text'])
                filename = f"{safe_name}.json"
                filepath = output_dir / filename
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(final_json, f, ensure_ascii=False, indent=2)
                logging.info(f"   ✅ Saved {filename}")

        await browser.close()
    logging.info(f"🎉 Scraping Complete for {category}!")

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", type=str, default="all", help="iphone, ipad, mac, watch, or all")
    args = parser.parse_args()
    
    target_cats = []
    if args.category == "all":
        target_cats = list(CATEGORIES.keys())
    elif args.category in CATEGORIES:
        target_cats = [args.category]
    else:
        logging.error(f"❌ Unknown category: {args.category}")
        return

    for cat in target_cats:
        await scrape_category(cat, CATEGORIES[cat])

if __name__ == "__main__":
    asyncio.run(main())
