
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

import pandas as pd
import glob
import yaml
import os
from src.processing.normalize import load_ai_model, ai_predict_key, RETAILER_MAP

def normalize_text(text):
    import re
    text = str(text).lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()

def main():
    print("🚀 Regenerating retailer_mapping.yaml using Llama 3B V2...")
    
    # 1. Load Model
    if not load_ai_model():
        print("❌ Failed to load model. Exiting.")
        return

    # 2. Scan all CSVs for unique products
    all_products = set()
    csv_files = glob.glob(str(PROJECT_ROOT / "data/raw/*/*.csv"))
    
    print(f"📂 Found {len(csv_files)} CSV files. Scanning for unique products...")
    
    product_registry = {} # {retailer_slug: {raw_name: last_seen_date}}
    
    for f in csv_files:
        try:
            filename = os.path.basename(f)
            # Extract retailer
            retailer_key = None
            for k, v in RETAILER_MAP.items():
                if k in filename:
                    retailer_key = v # Use Full Name "FPT Shop" as key in YAML
                    break
            
            if not retailer_key: continue
            
            # Read CSV
            try:
                df = pd.read_csv(f, sep=';', on_bad_lines='skip')
            except:
                df = pd.read_csv(f, sep=',', on_bad_lines='skip')
                
            col_name = 'Product_Name' if 'Product_Name' in df.columns else 'name'
            if col_name not in df.columns: continue
            
            if retailer_key not in product_registry:
                product_registry[retailer_key] = set()
                
            for name in df[col_name].dropna().unique():
                name_clean = name.strip()
                if len(name_clean) > 5:
                    product_registry[retailer_key].add(name_clean)
                    
        except Exception as e:
            pass

    # 3. Predict Keys
    mapping_data = {}
    
    total_count = sum(len(v) for v in product_registry.values())
    print(f"🧠 Predicting {total_count} unique products...")
    
    count = 0
    for retailer, products in product_registry.items():
        mapping_data[retailer] = {}
        for product in sorted(list(products)):
            pred = ai_predict_key(product)
            if pred and "unknown" not in pred.lower():
                mapping_data[retailer][product] = pred
            
            count += 1
            if count % 100 == 0:
                print(f"   Progress: {count}/{total_count}...", end='\r')
                
    print(f"\n✅ Prediction Complete. Saving to YAML...")

    # 4. Save to YAML
    output_path = PROJECT_ROOT / "catalog/retailer_mapping.yaml"
    
    # Custom Dumper to handle indentation and clean format
    class MyDumper(yaml.Dumper):
        def increase_indent(self, flow=False, indentless=False):
            return super(MyDumper, self).increase_indent(flow, False)

    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(mapping_data, f, Dumper=MyDumper, allow_unicode=True, default_flow_style=False, sort_keys=True)
        
    print(f"💾 Saved {len(mapping_data)} retailers to {output_path}")

if __name__ == "__main__":
    main()
