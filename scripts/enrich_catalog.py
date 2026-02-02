"""
Enrich Catalog Script
Merges detailed technical specifications from `catalog/specs/` into `catalog/apple_official_catalog.json`.
Handles mapping from Vietnamese scraped keys to standardized English keys.
"""
import json
import re
from pathlib import Path

CATALOG_PATH = Path("catalog/apple_official_catalog.json")
SPECS_DIR = Path("catalog/specs")

# Mapping Scraped Keys (VN) -> Canonical Keys (EN)
KEY_MAPPING = {
    "Chip": "chip",
    "Màn Hình": "display",
    "Camera": "back_camera",
    "Camera Trước": "front_camera",
    "Kết Nối": "connectivity",
    "Cổng Kết Nối": "ports",
    "Pin Và Nguồn Điện": "battery",
    "Xác Thực Bảo Mật": "security",
    "Tính Năng An Toàn": "safety",
    "Yên Tâm": "safety", # Alternate name
    "Kích Thước Và Trọng Lượng": "dimensions",
    "Cảm Biến": "sensors",
    "Thẻ SIM": "sim",
    "Loa": "speakers",
    "Micrô": "microphones"
}

def normalize_key(key):
    """
    Normalizes keys by removing footnote numbers and extra spaces.
    e.g. "Pin Và Nguồn Điện3" -> "Pin Và Nguồn Điện"
    """
    # Remove digits at the end or typically footnote markers
    clean = re.sub(r'\d+$', '', key).strip()
    return clean

def find_spec_file(category, product_name):
    """
    Tries to find the matching spec file.
    Strategy: 
    1. Exact filename match (Name -> Name.json) with spaces -> underscores
    2. Fuzzy match if needed
    """
    # Normalize product name to filename format used by scraper
    # usage in scraper: safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', model['text'])
    
    # Scraper replaced special chars with _, but let's replicate logic
    # Also scraper output filenames usually match the product name EXACTLY but with space replaced by _ 
    # and maybe some special char handling.
    
    # Let's try to construct the filename directly first
    safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', product_name)
    
    # Check distinct filename candidates
    candidates = [
        f"{safe_name}.json",
        f"{safe_name.replace('__', '_')}.json", # Double underscore fix
        f"{product_name}.json" 
    ]
    
    folder = SPECS_DIR / category.lower()
    if not folder.exists():
        return None
        
    for cand in candidates:
        fpath = folder / cand
        if fpath.exists():
            return fpath
            
    # If not found, try to look for partial matches in the folder
    # This is expensive but safer
    for file in folder.glob("*.json"):
        if safe_name in file.name:
            return file
            
    return None

def extract_critical_specs(raw_data):
    """
    Extracts and cleans specific fields using the dictionary mapping.
    """
    specs = {}
    
    for key, val in raw_data.items():
        if key.startswith("_"): continue # Skip metadata
        
        clean_k = normalize_key(key)
        
        # Check if we have a mapping for this key
        mapped_key = None
        for vn_key, en_key in KEY_MAPPING.items():
            if vn_key in clean_k:
                mapped_key = en_key
                break
        
        if mapped_key:
            # Value is usually a list of strings. Join them or keep list?
            # Catalog usually likes structured data. Let's keep as list for now or join with newlines.
            # actually list is better for searching.
            specs[mapped_key] = val
            
    return specs

def enrich():
    print("⏳ Loading catalog...")
    with open(CATALOG_PATH, 'r', encoding='utf-8') as f:
        catalog = json.load(f)
        
    stats = {"processed": 0, "enriched": 0, "missing": 0}
    
    for category, products in catalog.items():
        print(f"Processing Category: {category}")
        
        for prod in products:
            stats["processed"] += 1
            name = prod.get("name")
            
            spec_file = find_spec_file(category, name)
            
            if spec_file:
                # print(f"   MATCH: {name} -> {spec_file.name}")
                with open(spec_file, 'r', encoding='utf-8') as f:
                    raw_specs = json.load(f)
                
                enriched_specs = extract_critical_specs(raw_specs)
                prod["specs"] = enriched_specs
                stats["enriched"] += 1
            else:
                print(f"   ⚠️ MISSING SPEC FILE: {name}")
                stats["missing"] += 1
                prod["specs"] = {} # Initialize empty to show we tried

    print("💾 Saving enriched catalog...")
    with open(CATALOG_PATH, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
        
    print(f"\n🎉 DONE! Stats: {stats}")

if __name__ == "__main__":
    enrich()
