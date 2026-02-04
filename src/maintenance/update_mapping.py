
import pandas as pd
import yaml
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

# Now import
from src.utils.config import MAPPING_PATH, RETAILER_MAP

def update_mapping(csv_path):
    print(f"📥 Loading manual fixes from {csv_path}...")
    try:
        df = pd.read_csv(csv_path, sep=';', on_bad_lines='skip')
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    # Normalize Retailer Names
    # CSV has keys like 'mw', 'cps'. Need to map to full names if YAML uses full names?
    # RETAILER_MAP is {'2-mw': 'Mobile World', ...}
    # But usually mapping keys are the simple ones or the ones used in filenames.
    # Let's check how match_product uses it.
    # It uses `retailer_mapping[retailer_name or key]`.
    # Let's store by strict keys if possible, or names.
    # The csv has 'mw', 'viettel', 'cps'.
    
    # Reverse lookup for RETAILER_MAP
    # {'FPT Shop': '1-fpt', ...}
    # Actually retailer_key is what matters. 
    # Let's stick to the names used in the CSV for now, assuming they match what the processor sees.
    # Processor sees: "Mobile World" (from RETAILER_MAP).
    
    # We need to map 'mw' -> 'Mobile World'.
    
    simple_map = {
        'fpt': 'FPT Shop',
        'mw': 'Mobile World',
        'viettel': 'Viettel Store',
        'hoangha': 'HoangHa',
        'ddv': 'Di Động Việt',
        'cps': 'CellphoneS'
    }
    
    # Load existing YAML
    if MAPPING_PATH.exists():
        with open(MAPPING_PATH, 'r') as f:
            mapping = yaml.safe_load(f) or {}
    else:
        mapping = {}
        
    count = 0
    for _, row in df.iterrows():
        ret_code = str(row['Retailer']).lower().strip()
        retailer = simple_map.get(ret_code, ret_code) # Map mw -> Mobile World
        
        prod_name = str(row['Product_Name']).strip()
        mapped_key = str(row['mapped']).strip()
        
        if not prod_name or not mapped_key or mapped_key.lower() == 'nan':
            continue
            
        if retailer not in mapping:
            mapping[retailer] = {}
            
        # Update or Add
        mapping[retailer][prod_name] = mapped_key
        count += 1
        
    # Save
    with open(MAPPING_PATH, 'w', encoding='utf-8') as f:
        yaml.dump(mapping, f, allow_unicode=True, sort_keys=True)
        
    print(f"✅ Updated {count} mappings in {MAPPING_PATH}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python update_mapping.py <path_to_csv>")
    else:
        update_mapping(sys.argv[1])
