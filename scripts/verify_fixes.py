
import yaml
import os
from pathlib import Path

BASE_DIR = Path("/Users/brucehuynh/GitHub/daily-promotion")
MAPPING_PATH = BASE_DIR / "catalog/retailer_mapping.yaml"

def load_yaml(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def save_yaml(data, path):
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False)

def main():
    mapping = load_yaml(MAPPING_PATH)
    fixed_count = 0
    
    print(f"{'Retailer':<15} | {'Product Name':<50} | {'Old Key':<30} | {'New Key':<30}")
    print("-" * 130)
    
    for retailer, products in mapping.items():
        for p_name, key in products.items():
            original_key = key
            new_key = key
            
            p_lower = str(p_name).lower()
            k_lower = str(key).lower()
            
            # --- RULES ---
            
            # 1. Hallucination: Series 11 (Does not exist) -> Series 10
            # Condition: Key has 'series_11', but Product Name has 'series 10' or it's just wrong.
            if 'series_11' in k_lower:
                # If product name explicitly says "Series 11", keep it (though weird)? 
                # No, user confirms S11 doesn't exist. Map to S10.
                new_key = key.replace('series_11', 'series_10')
                
            # 2. Hallucination: iPad Air 5 -> ipad_a16 (Wrong)
            if 'ipad_a16' in k_lower:
                if 'air 5' in p_lower or 'air 2022' in p_lower:
                    new_key = 'ipad_air_thế_hệ_thứ_5'
                # If name is "iPad A16", keeping it is fine (mapped to Gen 10 in catalog).
                
            # 3. Hallucination: Apple Watch SE 2 -> apple_watch_se_2 (Standardize to SE 3 for 2024 model as per previous decision?)
            # Wait, I decided `apple_watch_se_3` = "SE 2 (2024)".
            # If key is `apple_watch_se_2`, should I upgrade to `apple_watch_se_3`? 
            # If product name says "2024" or "Gen 2", yes.
            if k_lower == 'apple_watch_se_2':
                 if '2024' in p_lower or 'se 2' in p_lower:
                     new_key = 'apple_watch_se_3_gps' 
            
            # 4. Hallucination: iPad Air 6 -> ipad_a16 (Wrong)
            if 'ipad_a16' in k_lower:
                 if 'air 6' in p_lower or 'm2' in p_lower:
                     # Check usage of 13 inch
                     if '13 inch' in p_lower or '13"' in p_lower:
                         new_key = 'ipad_air_13_inch_m2'
                     else:
                         new_key = 'ipad_air_11_inch_m2'

            # 5. Fix S11 Titanium -> S10 Titanium (Key fix)
            if 'apple_watch_series_11_titanium' in k_lower:
                new_key = new_key.replace('series_11', 'series_10')

            # --- END RULES ---
            
            if new_key != original_key:
                print(f"{retailer:<15} | {p_name[:50]:<50} | {original_key:<30} | {new_key:<30}")
                mapping[retailer][p_name] = new_key
                fixed_count += 1

    print("-" * 130)
    print(f"Total fixed: {fixed_count} mappings.")
    
    if fixed_count > 0:
        save_yaml(mapping, MAPPING_PATH)
        print(f"✅ Updated {MAPPING_PATH}")
    else:
        print("No changes needed. Mapping is clean.")

if __name__ == "__main__":
    main()
