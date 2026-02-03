import pandas as pd
import yaml
import os

# Config
DATA_FILE = "catalog/output/clean_data_2026-02-03.csv"
CATALOG_FILE = "catalog/product_catalog.yaml"

def load_data():
    if not os.path.exists(DATA_FILE):
        print(f"❌ File not found: {DATA_FILE}")
        return None
    return pd.read_csv(DATA_FILE)

def audit_mappings(df):
    print(f"🔍 Auditing {len(df)} records for inconsistencies...")
    
    errors = []
    
    # Define rules: (Keyword in Key, Forbidden Word in Original Name)
    # Note: Keys are like 'apple_watch_series_11_...'. 'original_name' is raw text.
    
    # 1. Product Line Mismatches
    rules = [
        ('series_11', 'se'),
        ('series_10', 'se'),
        ('series_9', 'se'),
        ('ipad_pro', 'air'),
        ('ipad_pro', 'mini'),
        ('ipad_air', 'pro '), # Space to avoid 'product' or similar if any
        ('ipad_air', 'mini'),
        ('ipad_mini', 'air'),
        ('ipad_mini', 'pro '),
        ('macbook_pro', 'air'),
        ('macbook_air', 'pro '),
        ('macbook_air', 'pro_'),
    ]
    
    # 2. Chip/Gen Mismatches
    chip_rules = [
        ('m4', ['m3', 'm2', 'm1']),
        ('m3', ['m4', 'm2', 'm1']),
        ('m2', ['m4', 'm3', 'm1']),
        ('m5', ['m4', 'm3', 'm2']),
    ]

    # 3. Screen Size Mismatches for iPads/Macs
    # Key token -> Forbidden in Name
    size_rules = [
        ('13', ['11 inch', '10.9 inch', '11"', '10.9"']),
        ('11', ['13 inch', '12.9 inch', '13"', '12.9"']),
        ('12.9', ['11 inch', '13 inch', '11"', '13"']), # Legacy
        ('14', ['16 inch', '16"']),
        ('16', ['14 inch', '14"']),
    ]
    
    for idx, row in df.iterrows():
        key = str(row['product_key']).lower()
        orig_name = str(row['original_name']).lower()
        retailer = row['retailer']
        
        # Rule Check 1: Forbidden keywords
        for key_token, bad_word in rules:
            if key_token in key:
                # Check bounds for bad word to avoid partial matches? 
                # e.g. "se" in "series" -> unwanted. 
                # So we check " se " or start/end bounds.
                # Simplify: check for word boundary regex or simple logic
                orig_tokens = set(orig_name.replace('(', ' ').replace(')', ' ').split())
                if bad_word.strip() in orig_tokens:
                     errors.append({
                         'Type': 'Line Mismatch',
                         'Retailer': retailer,
                         'Original': row['original_name'],
                         'Key': row['product_key'],
                         'Reason': f"Key has '{key_token}' but Name has '{bad_word}'"
                     })
                     
        # Rule Check 2: Chip Generation
        for key_chip, forbidden_chips in chip_rules:
            if f"_{key_chip}" in key or f"_{key_chip}_" in key: # Make sure matches key format extension
                for bad in forbidden_chips:
                     # Check if bad chip is in Original Name (strictly)
                     # e.g. "MacBook Air M2" shouldn't map to M3 key
                     tokens = orig_name.split()
                     if bad in tokens or f"({bad})" in orig_name:
                         errors.append({
                             'Type': 'Chip Mismatch',
                             'Retailer': retailer,
                             'Original': row['original_name'],
                             'Key': row['product_key'],
                             'Reason': f"Key has '{key_chip}' but Name has '{bad}'"
                         })

        # Rule Check 3: Screen Size
        for key_size, forbidden_sizes in size_rules:
             # Look for size indicator in key (e.g. _13_, _11_)
             if f"_{key_size}_" in key or key.endswith(f"_{key_size}"):
                 for bad_size in forbidden_sizes:
                     if bad_size in orig_name:
                         errors.append({
                             'Type': 'Size Mismatch',
                             'Retailer': retailer,
                             'Original': row['original_name'],
                             'Key': row['product_key'],
                             'Reason': f"Key has '{key_size}' but Name has '{bad_size}'"
                         })

    return pd.DataFrame(errors)

if __name__ == "__main__":
    df = load_data()
    if df is not None:
        err_df = audit_mappings(df)
        if not err_df.empty:
            print(f"⚠️ Found {len(err_df)} potential errors:")
            print(err_df.to_string())
            err_df.to_csv("mapping_audit_results.csv", index=False)
        else:
            print("✅ No obvious inconsistencies found.")
