
import yaml
import os
from pathlib import Path

BASE_DIR = Path("/Users/brucehuynh/GitHub/daily-promotion")
MAPPING_PATH = BASE_DIR / "catalog/retailer_mapping.yaml"
NEW_MAPPING_PATH = BASE_DIR / "catalog/new_ai_mappings.yaml"

def load_yaml(path):
    if not os.path.exists(path): return {}
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}

def save_yaml(data, path):
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False)

def correct_mapping(product_name, ai_key):
    """
    Apply manual corrections to AI hallucinations based on product name rules.
    """
    p_lower = product_name.lower()
    key = ai_key

    # 1. iPad Air 5 Correction
    if 'air 5' in p_lower or 'air 2022' in p_lower:
        if 'ipad' in p_lower:
            key = 'ipad_air_thế_hệ_thứ_5'
            
    # 2. Apple Watch Series 10 Correction (AI mostly mapped to S11)
    if 'series 10' in p_lower or 's10' in p_lower:
        # Check material/connectivity usually implied by AI key, but fix the version
        if 'series_11' in key:
            key = key.replace('series_11', 'series_10')
            
    # 3. Apple Watch SE Fix
    # If "SE 2" or "SE 2024" or "SE 2023", map to our SE 2024 key (apple_watch_se_3)
    if 'watch se' in p_lower:
        if '2024' in p_lower or 'se 2' in p_lower or 'se 2023' in p_lower:
             # Preserve suffix (gps/lte) from AI if valid
             suffix = ""
             if 'lte' in key or 'gps_cellular' in key: suffix = "_lte"
             elif 'gps' in key: suffix = "_gps"
             
             key = f"apple_watch_se_3{suffix}"
             if key == "apple_watch_se_3": key = "apple_watch_se_3_gps" # Default to GPS if unknown

    # 4. iPad Air 6 (M2) Correction
    if 'air 6' in p_lower or 'm2' in p_lower:
        if 'ipad' in p_lower and 'air' in p_lower:
             if '13' in p_lower:
                 key = 'ipad_air_13_inch_m2'
             else:
                 key = 'ipad_air_11_inch_m2'

    # 5. Fix "A16" hallucination for known models
    # If AI mapped to ipad_a16 but it's clearly something else
    if key.startswith('ipad_a16'):
        if 'air 5' in p_lower: key = 'ipad_air_thế_hệ_thứ_5'
        if 'gen 10' in p_lower: key = 'ipad_gen_10' 
        
    return key

def main():
    main_map = load_yaml(MAPPING_PATH)
    
    # Load sources
    sources = [NEW_MAPPING_PATH, BASE_DIR / "catalog/ai_suggested_mapping.yaml"]
    new_map = {}
    
    for src in sources:
        data = load_yaml(src)
        for retailer, products in data.items():
            if retailer not in new_map: new_map[retailer] = {}
            new_map[retailer].update(products)
    
    added_count = 0
    
    print("Processing new mappings...")
    
    for retailer, products in new_map.items():
        if retailer not in main_map:
            main_map[retailer] = {}
            
        if main_map[retailer] is None:
             main_map[retailer] = {}
            
        for p_name, ai_key in products.items():
            # Skip if already exists
            if p_name in main_map[retailer]:
                continue
                
            # Apply corrections
            final_key = correct_mapping(p_name, ai_key)
            
            # Add to main map
            main_map[retailer][p_name] = final_key
            added_count += 1
            
            # Log changes
            if final_key != ai_key:
                print(f"  [Fixed] {p_name} -> {final_key} (was {ai_key})")
            else:
                pass
                # print(f"  [Added] {p_name} -> {final_key}")

    print(f"\nMerged {added_count} new mappings into {MAPPING_PATH}")
    save_yaml(main_map, MAPPING_PATH)
    print("Done!")

if __name__ == "__main__":
    main()
