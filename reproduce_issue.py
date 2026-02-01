
import pandas as pd
import yaml
import re

# Load Catalog
with open('product_catalog_golden_v2.yaml', 'r') as f:
    catalog = yaml.safe_load(f)

# Mock simple match_product logic (copied relevant parts from 10-Normalize...)
def normalize_text(text):
    if not isinstance(text, str): return ""
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    return text.strip()

def generate_catalog_tokens(catalog):
    cat_tokens = {}
    for key, info in catalog.items():
        name = normalize_text(info['name'])
        tokens = set(name.split())
        cat_tokens[key] = tokens
    return cat_tokens

CAT_TOKENS = generate_catalog_tokens(catalog)

def match_product(raw_name, raw_specs=""):
    norm_name = normalize_text(raw_name)
    input_tokens = set(norm_name.split())
    
    best_key = None
    max_overlap = 0
    
    for key, cat_tokens in CAT_TOKENS.items():
        overlap = len(input_tokens.intersection(cat_tokens))
        if overlap > max_overlap:
            max_overlap = overlap
            best_key = key
            
    return best_key, max_overlap

# Check DDV file
try:
    df = pd.read_csv('content/2026-01-31/5-ddv-2026-01-31.csv')
    print(f"Loaded DDV CSV with {len(df)} rows")
    
    m3_rows = df[df['product_name'].str.contains('M3', case=False, na=False)]
    print(f"Found {len(m3_rows)} rows with 'M3'")
    
    if not m3_rows.empty:
        sample = m3_rows.iloc[0]
        name = sample['product_name']
        print(f"Sample M3 Product: {name}")
        
        key, score = match_product(name)
        print(f"Match Result: {key} (Score: {score})")
        
        # Test specific granular keys
        print("\nChecking overlap for granular keys:")
        norm_name = normalize_text(name)
        tokens = set(norm_name.split())
        
        for k in ['macbook_pro_14_m3', 'macbook_pro_14_m3_pro_max', 'macbook_pro_16_m3_pro_max']:
            if k in CAT_TOKENS:
                print(f"{k}: {tokens.intersection(CAT_TOKENS[k])}")
            else:
                print(f"{k} NOT IN CATALOG")

except Exception as e:
    print(f"Error: {e}")
