
import pandas as pd
import yaml
import os

# Paths
CSV_PATH = 'analysis/normalized/normalized_mapping_2026-02-01.csv'
YAML_PATH = 'analysis/reference/retailer_mapping_v1.yaml'

def generate_yaml():
    if not os.path.exists(CSV_PATH):
        print(f"Error: {CSV_PATH} not found.")
        return

    df = pd.read_csv(CSV_PATH)
    
    # Structure: Retailer -> Original Name -> Product Key
    mapping = {}
    
    for _, row in df.iterrows():
        retailer = str(row['retailer']).strip()
        orig_name = str(row['original_name']).strip()
        prod_key = str(row['product_key']).strip()
        
        if pd.isna(retailer) or pd.isna(orig_name) or pd.isna(prod_key):
            continue
            
        if retailer not in mapping:
            mapping[retailer] = {}
            
        mapping[retailer][orig_name] = prod_key
        
    # Write to YAML
    with open(YAML_PATH, 'w', encoding='utf-8') as f:
        yaml.dump(mapping, f, allow_unicode=True, default_flow_style=False, sort_keys=True)
        
    print(f"Generated {YAML_PATH} with {sum(len(v) for v in mapping.values())} entries.")

if __name__ == "__main__":
    generate_yaml()
