import yaml
import json
import os
import re
from pathlib import Path

# Paths
BASE_DIR = Path("/Users/brucehuynh/GitHub/daily-promotion")
REF_CATALOG_PATH = BASE_DIR / "product_catalog_golden.yaml"
COMPARE_DATA_DIR = BASE_DIR / "analysis/scraped_data/compare_specs"
OUTPUT_PATH = BASE_DIR / "product_catalog_golden_v2.yaml"

def slugify(text):
    text = text.lower()
    text = re.sub(r'\s+', '_', text)
    text = re.sub(r'[^\w\-_]', '', text)
    return text

def clean_colors(raw_list):
    if not raw_list: return []
    cleaned = []
    # Keywords to skip
    skip_keywords = ["điều hướng", "liên kết", "xem bằng", "mua", "tìm hiểu", "giá", "từ", "đ", "hình ảnh"]
    
    for item in raw_list:
        lower = item.lower()
        if any(k in lower for k in skip_keywords):
            continue
        # Remove common prefixes like "Nhôm ", "Titan " if desired, or keep them?
        # User feedback implies "Titan" is a variant. Better keep full string.
        # But remove newlines
        item = item.replace('\n', ' ').strip()
        if item and len(item) < 50: # Avoid long descriptions
             cleaned.append(item)
    return sorted(list(set(cleaned)))

def clean_storage(raw_list):
    if not raw_list: return []
    cleaned = []
    for item in raw_list:
        # Extract XGB, XTB
        matches = re.findall(r'(\d+[GT]B)', item)
        cleaned.extend(matches)
    
    # Sort
    def storage_key(s):
        if 'TB' in s:
            return float(re.search(r'\d+', s).group()) * 1024
        match = re.search(r'\d+', s)
        return float(match.group()) if match else 0
        
    return sorted(list(set(cleaned)), key=storage_key)

def clean_sizes(raw_list, category):
    if not raw_list: return []
    cleaned = []
    
    # Allowed sizes whitelist/patterns to differentiate from dimensions
    # Watch: 38-49mm
    # iPad/Mac: 10-16 inch
    # iPhone: Display size usually 4.7, 5.4, 6.1, 6.7, 6.3, 6.9 inch
    
    for item in raw_list:
        # Match number + unit (support comma/dot decimals)
        # e.g. "6,7 inch", "6.1 inch", "42mm"
        matches = re.finditer(r'(\d+(?:[.,]\d+)?)\s*(inch|mm)', item, re.IGNORECASE)
        for m in matches:
            val_str = m.group(1).replace(',', '.')
            val = float(val_str)
            unit = m.group(2).lower()
            
            # Filter based on category logic
            is_valid = False
            
            if category == 'watch':
                # Case sizes usually 38 to 49 mm
                if unit == 'mm' and 38 <= val <= 49:
                    is_valid = True
            elif category in ['ipad', 'mac']:
                # Screen sizes usually 8 to 16 inch
                if unit == 'inch' and 7.9 <= val <= 17:
                    is_valid = True
            elif category == 'iphone':
                # Screen sizes 4.0 careful to 6.9
                if unit == 'inch' and 4.0 <= val <= 7.0:
                    is_valid = True
            
            if is_valid:
                # Format standard
                if unit == 'inch':
                    cleaned.append(f"{val:g} inch")
                else:
                    cleaned.append(f"{val:g}mm")
                    
    return sorted(list(set(cleaned)))

def extract_connectivity(data, category):
    # Primarily for Watch/iPad
    connectivities = set()
    
    # Check all keys for connectivity related keywords
    all_text = json.dumps(data, ensure_ascii=False)
    
    if "GPS + Cellular" in all_text:
        connectivities.add("GPS + Cellular")
    if "GPS" in all_text and category == 'watch':
        connectivities.add("GPS")
    if "Wi-Fi + Cellular" in all_text:
         connectivities.add("Wi-Fi + Cellular")
    if "Wi-Fi" in all_text and category == 'ipad':
         connectivities.add("Wi-Fi")
         
    return sorted(list(connectivities))

def main():
    # 1. Load Reference
    if REF_CATALOG_PATH.exists():
        with open(REF_CATALOG_PATH, 'r') as f:
            catalog = yaml.safe_load(f) or {}
    else:
        catalog = {}

    # 2. Iterate Categories
    # Proper Case Mapping
    cat_map = {
        'iphone': 'iPhone',
        'ipad': 'iPad',
        'mac': 'Mac',
        'watch': 'Watch'
    }
    
    for cat, display_cat in cat_map.items():
        cat_dir = COMPARE_DATA_DIR / cat
        if not cat_dir.exists():
            print(f"Skipping {cat}, no scraped data.")
            continue
            
        print(f"Processing {cat}...")
        for json_file in cat_dir.glob("*.json"):
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            name = data.get('device_name', '')
            if not name: continue
            
            # Normalize name differently for matching?
            # Existing catalog keys are like `iphone_16`.
            # New keys might be `iphone_13_pro`.
            key = slugify(name)
            
            # Prepare Entry
            if key not in catalog:
                catalog[key] = {
                    "name": name,
                    "category": display_cat, 
                    "url": None # Comparison derived
                }
            
            entry = catalog[key]
            
            # EXTRACT DATA
            # Colors
            color_keys = [k for k in data.keys() if "màu" in k.lower() or "finish" in k.lower()]
            raw_colors = []
            for k in color_keys:
                raw_colors.extend(data[k])
            
            new_colors = clean_colors(raw_colors)
            if new_colors:
                # Merge with existing
                existing = set(entry.get('colors', []))
                existing.update(new_colors)
                entry['colors'] = sorted(list(existing))

            # Storage
            storage_keys = [k for k in data.keys() if "dung lượng" in k.lower() or "capacity" in k.lower()]
            raw_storage = []
            for k in storage_keys:
                raw_storage.extend(data[k])
            
            new_storage = clean_storage(raw_storage)
            if new_storage:
                 # Prefer scraping over existing if scraping is non-empty? Or merge?
                 # Storage usually is fixed set. Merge is safe.
                existing = set(entry.get('storage', []))
                existing.update(new_storage)
                # Sort again
                entry['storage'] = clean_storage(list(existing))

            # Sizes
            size_keys = [k for k in data.keys() if "màn hình" in k.lower() or "vỏ" in k.lower() or "kích thước" in k.lower()]
            raw_sizes = []
            for k in size_keys:
                raw_sizes.extend(data[k])
            
            new_sizes = clean_sizes(raw_sizes, cat)
            if new_sizes:
                existing = set(entry.get('sizes', []))
                existing.update(new_sizes)
                entry['sizes'] = sorted(list(existing))
                
            # Connectivity (New Field)
            conn = extract_connectivity(data, cat)
            if conn:
                existing = set(entry.get('connectivity', []))
                existing.update(conn)
                entry['connectivity'] = sorted(list(existing))
            
            # Add source flag
            entry['source'] = 'official_combined'

    # 3. Save
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        yaml.dump(catalog, f, allow_unicode=True, sort_keys=False)
    
    print(f"Generated {OUTPUT_PATH} with {len(catalog)} products.")

if __name__ == "__main__":
    main()
