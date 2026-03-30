
import pandas as pd
import yaml
import os

INPUT_CSV = "analysis/normalized/normalized_mapping_2026-02-01.csv"
OUTPUT_YAML = "analysis/reference/retailer_mapping_v1.yaml"

def main():
    if not os.path.exists(INPUT_CSV):
        print(f"Error: {INPUT_CSV} not found.")
        return

    df = pd.read_csv(INPUT_CSV)
    
    # Structure: Retailer -> Original Name -> Golden Key
    mapping = {}

    print(f"Loading {len(df)} rows from {INPUT_CSV}...")

    for _, row in df.iterrows():
        retailer = row['retailer']
        original_name = str(row['original_name']).strip()
        product_key = row['product_key']

        if pd.isna(product_key): continue
        
        if retailer not in mapping:
            mapping[retailer] = {}
        
        # We only map the Product Name. 
        # Future scripts will look up: mapping[retailer].get(current_row_name)
        mapping[retailer][original_name] = product_key

    # Save to YAML
    os.makedirs(os.path.dirname(OUTPUT_YAML), exist_ok=True)
    
    with open(OUTPUT_YAML, 'w', encoding='utf-8') as f:
        yaml.dump(mapping, f, allow_unicode=True, sort_keys=True)
        
    print(f"Successfully saved mapping to {OUTPUT_YAML}")
    print(f"Total retailers mapped: {len(mapping)}")
    for r in mapping:
        print(f"  - {r}: {len(mapping[r])} products")

if __name__ == "__main__":
    main()
