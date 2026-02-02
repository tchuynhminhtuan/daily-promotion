
import pandas as pd
import yaml

FIX_CSV = "catalog/output/unmatched_err_2026-02-02-fix.csv"
MAPPING_FILE = "catalog/retailer_mapping.yaml"

def main():
    # Read fixed CSV (semicolon delimited)
    df = pd.read_csv(FIX_CSV, sep=';')
    
    # Build correction map: (retailer, orig_name) -> correct_key
    corrections = {}
    for _, row in df.iterrows():
        retailer = row['retailer']
        orig_name = str(row['original_name'])
        correct_key = str(row['potential_name'])
        
        if pd.isna(row['potential_name']) or pd.isna(row['original_name']):
            continue
        
        # Normalize weird raw names
        if orig_name.startswith("apple_watch_se_2 GPS"):
            orig_name = orig_name.replace("apple_watch_se_2", "Apple Watch SE 2")
        
        corrections[(retailer, orig_name)] = correct_key
    
    # Load existing YAML
    with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
        existing = yaml.safe_load(f) or {}
    
    updated_count = 0
    added_count = 0
    
    # Fix entries
    for (retailer, name), correct_key in corrections.items():
        if retailer not in existing:
            existing[retailer] = {}
        
        current = existing[retailer].get(name)
        if current is None:
            # Add new entry
            existing[retailer][name] = correct_key
            added_count += 1
            print(f"+ ADD: {retailer}: {name} -> {correct_key}")
        elif current != correct_key:
            # Update wrong entry
            print(f"~ FIX: {retailer}: {name}: {current} -> {correct_key}")
            existing[retailer][name] = correct_key
            updated_count += 1
        # else: already correct, skip
    
    # Save
    with open(MAPPING_FILE, 'w', encoding='utf-8') as f:
        yaml.dump(existing, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    
    print(f"\n✅ Added {added_count}, Fixed {updated_count} mappings in {MAPPING_FILE}")

if __name__ == "__main__":
    main()
