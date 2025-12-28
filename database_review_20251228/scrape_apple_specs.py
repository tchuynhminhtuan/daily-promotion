import asyncio
import json
import os
from playwright.async_api import async_playwright
import re

# Configuration
BASE_URL = "https://support.apple.com/en-us/docs"
OUTPUT_FILE = "apple_products_db.json"
MAX_CONCURRENT_PAGES = 5 # Be polite but efficient
categories_to_scan = ["Mac", "iPad", "iPhone", "Watch", "AirPods"]

async def scrape_tech_specs(page, url):
    """Extracts specs from a Tech Specs page."""
    try:
        await page.goto(url, timeout=60000)
        await page.wait_for_load_state("domcontentloaded")
        
        # Scrape all H3 sections (common format for Apple Specs)
        # Structure often: H3 (Title) -> UL (Specs) or P (Specs)
        
        specs = {}
        
        # Evaluate to get structured data
        data = await page.evaluate('''() => {
            const sections = {};
            // Try standard Apple Spec format (H3 headers followed by lists/content)
            document.querySelectorAll('h3').forEach(h3 => {
                const title = h3.innerText.trim();
                let content = [];
                let next = h3.nextElementSibling;
                while (next && next.tagName !== 'H3') {
                    if (next.innerText.trim()) {
                        content.push(next.innerText.trim());
                    }
                    next = next.nextElementSibling;
                }
                sections[title] = content;
            });
            
            // Fallback for newer pages that might use different structures (divs)
            if (Object.keys(sections).length === 0) {
                 document.querySelectorAll('.tech-specs-section').forEach(section => {
                     // logic for alternative layouts if needed
                 });
            }
            return sections;
        }''')
        
        return data, url
    except Exception as e:
        print(f"Error scraping specs at {url}: {e}")
        return None, url

async def process_model(context, model_name, model_url, sem):
    """Process a single model: Find Tech Specs link -> Scrape Specs."""
    async with sem:
        page = await context.new_page()
        try:
            print(f"  Processing Model: {model_name}...")
            await page.goto(model_url, timeout=30000)
            
            # Look for "Tech Specs" or "Technical Specifications" link
            # VI: "Thông số kỹ thuật"
            spec_link = await page.get_by_role("link", name=re.compile(r"(Tech(nical)? Specs|Thông số kỹ thuật)", re.IGNORECASE)).first.get_attribute("href")
            
            if spec_link:
                # Handle relative URLs if any (browsers handle this, but get_attribute returns exactly what's in DOM)
                if not spec_link.startswith("http"):
                    # Construct absolute ULR if needed, but Apple docs usually link to support.apple.com/kb/SP...
                    if spec_link.startswith("/"):
                        spec_link = "https://support.apple.com" + spec_link
                
                print(f"    -> Found Specs: {spec_link}")
                specs, final_url = await scrape_tech_specs(page, spec_link)
                return {
                    "Model": model_name,
                    "Family": "Unknown", # Filled by caller
                    "Specs": specs,
                    "Docs_Url": model_url,
                    "Specs_Url": final_url
                }
            else:
                print(f"    x No Tech Specs link found for {model_name}")
                return None
                
        except Exception as e:
            print(f"    Error processing model {model_name}: {e}")
            return None
        finally:
            await page.close()

async def process_category(context, category_name, category_url):
    """Process a Category page to find all Models."""
    page = await context.new_page()
    models = []
    try:
        print(f"Scanning Category: {category_name} ({category_url})...")
        await page.goto(category_url, timeout=30000)
        await page.wait_for_load_state("networkidle")
        
        # --- Handle "Load More" / Pagination ---
        # Apple Docs pages often use a "Show more results" button at bottom.
        # Button selector usually: button with text "Show more results" or class "show-more".
        # We'll try to click it until it disappears.
        print("  Checking for infinite scroll/load more...")
        try:
            while True:
                # Look for typical "Show more" button. Adjustable based on inspecting actual page DOM if needed.
                # Common classes: .as-load-more-button, or check text.
                # In Vietnamese: "Hien thi them ket qua" -> "Hiện thêm kết quả" ?
                # Or simply scroll to bottom to trigger if it's infinite scroll.
                # Let's try scrolling first + generic button check.
                
                previous_height = await page.evaluate("document.body.scrollHeight")
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.try_get_by_role("button", name=re.compile(r"(Show more|Hiển thị thêm|Load more)", re.IGNORECASE)).click(timeout=2000)
                await page.wait_for_timeout(2000) # Wait for load
                
                new_height = await page.evaluate("document.body.scrollHeight")
                if new_height == previous_height:
                    break # No more content loaded
        except:
            pass # Button not found or end of list, continue
            
        # Extract all product links
        # Structure: usually a list of links inside the main content
        # We look for links containing "/docs/" but NOT same as category url
        
        # Robust extraction: Get ALL links and filter path
        links = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll('a')).map(a => ({
                text: a.innerText.trim(),
                href: a.href
            }));
        }''')
        
        print(f"  Debug: Found {len(links)} total links on page.")
        # if len(links) > 0: print(f"  Sample link: {links[50]}") 
        
        # Filter: Must contain category path (e.g. /docs/mac/) and have a number id (usually)
        # Apple model docs usually look like: .../docs/mac/300178
        
        target_path = f"/docs/{category_name.lower()}/"
        clean_links = []
        seen = set()
        
        for link in links:
            href = link['href']
            text = link['text']
            
            # Must be inside the category subfolder
            if target_path not in href: continue
            
            # Skip the category root itself
            if href.rstrip('/') == category_url.rstrip('/'): continue
            
            # Skip "Browse by Product" or "Vintages" if any
            if "Browse by" in text: continue
            if not text: continue
            if href in seen: continue
            
            # Heuristic: Model pages usually end in a number or have specific structure?
            # Let's just take everything in the subfolder for now and let the "Tech Specs" check filter them out.
            
            clean_links.append((text, href))
            seen.add(href)
            
        print(f"  Found {len(clean_links)} potential models in {category_name}.")
        return clean_links
        
    finally:
        await page.close()

def is_relevant_model(name):
    """
    Keep ALL models as per user request to scrape 'everything'.
    """
    return True
    
    # 1. Year Check
    if re.search(r'202[0-9]', name_check): return True
    
    # 2. Chip Check
    if re.search(r'\bM[1-9]', name_check): return True
    
    # 3. iPhone Check (iPhone 11, 12, 13, 14, 15, 16...)
    if "IPHONE" in name_check:
        if re.search(r'1[1-9]', name_check): return True # 11-19
        if "SE" in name_check and "3RD" in name_check: return True
        
    # 4. iPad Check
    if "IPAD" in name_check:
        # Keep generalized iPads? e.g. "iPad (10th generation)"
        if re.search(r'\b(9|10)TH\b', name_check): return True # 9th, 10th
        if "AIR" in name_check and re.search(r'[4-9]TH', name_check): return True # Air 4+
        if "MINI" in name_check and re.search(r'[6-9]TH', name_check): return True # Mini 6+
        if "PRO" in name_check: return True # Keep all Pros for safety? Or filter generations.
        # "iPad Pro 11-inch (3rd generation)" (2021) matches M1 check usually? M1 iPad Pro is 2021.
        # "iPad Pro 12.9-inch (5th generation)" (2021) M1.
        
    # 5. Watch Check
    if "WATCH" in name_check:
        if "SERIES" in name_check and re.search(r'[6-9]|10', name_check): return True
        if "ULTRA" in name_check or "SE" in name_check: return True
        
    # 6. AirPods (All usually relevant as few models)
    if "AIRPODS" in name_check: return True
    
    return False

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Load existing DB if available to merge/resume
        db = {}
        if os.path.exists(OUTPUT_FILE):
             try:
                 with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                     db = json.load(f)
                 print(f"📂 Loaded {len(db)} existing models from {OUTPUT_FILE}")
             except: pass

        sem = asyncio.Semaphore(MAX_CONCURRENT_PAGES)
        
        # Custom Request: VIETNAMESE ONLY
        locales = ["vi-vn"]
        
        for locale in locales:
            print(f"🌍 Starting scrape for locale: {locale}")
            base_url = f"https://support.apple.com/{locale}/docs"
            
            locale_tasks = []
            
            for cat in categories_to_scan:
                cat_url = f"{base_url}/{cat.lower()}"
                
                # Get Models for this category
                try:
                    # Increased timeout and added retry logic could be good, but just increasing timeout for now
                    print(f"  Scanning {cat}...")
                    model_links = await process_category(context, cat, cat_url)
                    
                    # Create tasks for each RELEVANT model
                    skipped = 0
                    for name, url in model_links: 
                        if is_relevant_model(name):
                            locale_tasks.append(process_model(context, name, url, sem))
                        else:
                            skipped += 1
                    
                    if skipped: print(f"    Skipped {skipped} old/irrelevant models in {cat}.")
                except Exception as e:
                    print(f"  ❌ Error scanning category {cat}: {e}")
            
            if not locale_tasks:
                continue
                
            print(f"🚀 Processing {len(locale_tasks)} models for {locale}...")
            
            # Use as_completed to save incrementally as requested
            count = 0
            for future in asyncio.as_completed(locale_tasks):
                try:
                    res = await future
                    if isinstance(res, dict):
                        # Update DB
                        db[res['Model']] = res
                        count += 1
                        
                        # SAVE IMMEDIATELY
                        try:
                            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                                json.dump(db, f, ensure_ascii=False, indent=2)
                            print(f"  💾 Saved {res['Model']}")
                        except Exception as e:
                            print(f"  ⚠️ Save failed for {res['Model']}: {e}")
                            
                    elif isinstance(res, Exception):
                        print(f"    Task failed: {res}")
                except Exception as e:
                    print(f"    Future exception: {e}")
            
            print(f"✅ Finished {locale}. Total models saved: {len(db)}")
                    
            # Save
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(db, f, indent=2, ensure_ascii=False)
                
            print(f"✅ Saved {len(db)} total models after {locale}.")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
