
import pandas as pd
import yaml
import glob
import os
from pathlib import Path

BASE_DIR = Path("/Users/brucehuynh/GitHub/daily-promotion")
CONTENT_DIR = BASE_DIR / "data/raw/2026-02-01"
MAPPING_PATH = BASE_DIR / "catalog/retailer_mapping.yaml"

RETAILER_MAP = {
    '1-fpt': 'FPT Shop',
    '2-mw': 'Mobile World', 
    '3-viettel': 'Viettel Store',
    '4-hoangha': 'HoangHa',
    '5-ddv': 'Di Động Việt',
    '6-cps': 'CellphoneS'
}

def load_mapping():
    with open(MAPPING_PATH, 'r') as f:
        return yaml.safe_load(f)

def analyze():
    mapping = load_mapping()
    csv_files = glob.glob(str(CONTENT_DIR / "*.csv"))
    
    total_products = 0
    mapped_count = 0
    unmapped_count = 0
    
    print(f"{'Retailer':<20} | {'Total':<8} | {'Mapped':<8} | {'Unmapped':<8} | {'Coverage':<8}")
    print("-" * 65)

    for f in csv_files:
        filename = os.path.basename(f)
        retailer_key = "-".join(filename.split('-')[:2])
         # Fix key lookup logic to match normalize.py
        if retailer_key not in RETAILER_MAP:
             for k in RETAILER_MAP:
                 if k in filename:
                     retailer_key = k
                     break
                     
        retailer_name = RETAILER_MAP.get(retailer_key, "Unknown")
        
        try:
            try:
                df = pd.read_csv(f, sep=';', on_bad_lines='skip')
            except:
                df = pd.read_csv(f, sep=',', on_bad_lines='skip')
                
            cols = df.columns
            name_col = next((c for c in ['Product_Name', 'name', 'Name'] if c in cols), None)
            
            if not name_col:
                continue

            r_map = mapping.get(retailer_name, {})
            
            local_mapped = 0
            local_unmapped = 0
            
            for _, row in df.iterrows():
                p_name = str(row[name_col]).strip()
                if p_name in r_map:
                    local_mapped += 1
                else:
                    local_unmapped += 1
            
            total = len(df)
            coverage = (local_mapped / total * 100) if total > 0 else 0
            
            print(f"{retailer_name:<20} | {total:<8} | {local_mapped:<8} | {local_unmapped:<8} | {coverage:.1f}%")
            
            total_products += total
            mapped_count += local_mapped
            unmapped_count += local_unmapped
            
        except Exception as e:
            print(f"Error reading {f}: {e}")

    print("-" * 65)
    total_coverage = (mapped_count / total_products * 100) if total_products > 0 else 0
    print(f"{'TOTAL':<20} | {total_products:<8} | {mapped_count:<8} | {unmapped_count:<8} | {total_coverage:.1f}%")

if __name__ == "__main__":
    analyze()
