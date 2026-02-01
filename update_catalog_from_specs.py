
import os
import sys
import ruamel.yaml
import pandas as pd
import re

# Setup paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
YAML_PATH = os.path.join(BASE_DIR, 'analysis', 'reference', 'product_catalog.yaml')
CONTENT_DIR = os.path.join(BASE_DIR, 'content')
DATE_STR = "2026-01-31"

# Import Normalizer logic manually to avoid dependency issues or circular imports
class ProductNormalizer:
    def __init__(self):
        self.storage_patterns = [
            r'(?:Bộ nhớ trong|ROM|Dung lượng|Ổ cứng)[:\s]+(\d+[\s]*[GgTt][Bb])',
            r'(\d+[\s]*[GgTt][Bb])\s*(?:ROM|Bộ nhớ)',
        ]
        self.name_storage_pattern = re.compile(r'\b\d+[\s]*[GgTt][Bb]\b', re.IGNORECASE)
        self.watch_material_patterns = {
            "Titan": r'(Titan|Titanium)',
            "Nhôm": r'(Nhôm|Aluminum)',
            "Thép": r'(Thép|Steel|Stainless)'
        }
        self.watch_conn_patterns = {
            "LTE": r'(LTE|Cellular|eSIM|4G|5G)',
            "GPS": r'(GPS)'
        }

    def enrich_name(self, name, specs):
        if pd.isna(specs) or pd.isna(name): return name
        name_str = str(name).strip()
        specs_str = str(specs)
        
        if "watch" in name_str.lower():
            if re.search(r'(?:eSIM|Nghe gọi độc lập|Cellular|4G|5G)', specs_str, re.IGNORECASE) and not re.search(r'(?:LTE|Cellular|4G|5G)', name_str, re.IGNORECASE):
                if "GPS" in name_str.upper(): name_str = name_str.replace("GPS", "GPS + Cellular")
                else: name_str += " LTE"
            for mat_key, pattern in self.watch_material_patterns.items():
                if not re.search(pattern, name_str, re.IGNORECASE) and re.search(pattern, specs_str, re.IGNORECASE):
                    name_str += f" Viền {mat_key}"
            return name_str

        if self.name_storage_pattern.search(name_str): return name_str
        for pattern in self.storage_patterns:
            match = re.search(pattern, specs_str, re.IGNORECASE)
            if match:
                return f"{name_str} ({match.group(1).upper().replace(' ', '')})"
        return name_str

def main():
    print(f"Loading YAML from {YAML_PATH}...")
    yaml = ruamel.yaml.YAML()
    yaml.preserve_quotes = True
    
    with open(YAML_PATH, 'r', encoding='utf-8') as f:
        catalog = yaml.load(f)

    # Build Reverse Map: Normalized/Rich Name -> Canonical Key
    # We try to match enriched names to existing keys
    # Key strategy: Create valid "Rich Keys" from existing keys
    
    # Load Data
    normalizer = ProductNormalizer()
    day_dir = os.path.join(CONTENT_DIR, DATE_STR)
    if not os.path.exists(day_dir):
        print("Date directory not found.")
        return

    csv_files = [f for f in os.listdir(day_dir) if f.endswith('.csv')]
    
    updates_count = 0
    
    for filename in csv_files:
        path = os.path.join(day_dir, filename)
        try:
            df = pd.read_csv(path, sep=None, engine='python')
            print(f"Processing {filename}...")
            
            if 'Tech_Specs' not in df.columns:
                print(f"  Skipping {filename} (No specs)")
                continue
                
            for _, row in df.iterrows():
                raw_name = row.get('Product_Name') or row.get('Product Name')
                if not raw_name: continue
                
                raw_name = str(raw_name).strip()
                specs = row.get('Tech_Specs', '')
                
                # 1. Generate Rich Name using Specs
                rich_name = normalizer.enrich_name(raw_name, specs)
                
                # 2. Find matching entry in YAML
                # Strategy:
                # - Check if raw_name is already in any variant (exact match) -> Skip
                # - Check if rich_name looks like a key or variant
                
                found_key = None
                
                # Simple O(N) scan - can be optimized
                for key, data in catalog.items():
                    # Check variants
                    if 'variants' in data and data['variants']:
                        if raw_name in data['variants']:
                            found_key = key
                            break 
                        # Also check if the RICH name matches a variant (less likely but possible)
                
                if found_key:
                    # Already exists
                    continue
                    
                # If not found, try to fuzzy match the RICH NAME to a Key
                # e.g. Rich Name: "iPhone 13 (128GB)" -> Match to key "iphone_13_128gb"
                # Simplify Rich Name to Key format
                simple_rich = rich_name.lower().replace('(', '').replace(')', '').replace(' ', '_').replace('-', '_').replace('+', '')
                simple_rich = re.sub(r'_+', '_', simple_rich)
                
                # Strategy: Find ALL keys that are contained in simple_rich OR simple_rich is contained in key
                # Then pick the LONGEST key matches to be more specific (e.g. prefer 'iphone_13_128gb' over 'iphone_13')
                possible_keys = []
                
                for key in catalog.keys():
                    if key in simple_rich or simple_rich in key:
                        # Storage check: If key has storage, rich name must match it
                        # Extract storage from both
                        sk = re.search(r'(\d+gb|\d+tb)', key)
                        sr = re.search(r'(\d+gb|\d+tb)', simple_rich)
                        
                        if sk and sr:
                            if sk.group(1) != sr.group(1):
                                continue # Mismatch storage explicitly
                        elif sk and not sr:
                            # Key has storage but Name doesn't? Unlikely if we did enrichment right.
                            # But if Name is "iPhone 13" and Key is "iphone_13_128gb", maybe we shouldn't match?
                            # Let's be safe: if Key is specific, Name must be specific.
                            continue
                            
                        possible_keys.append(key)

                best_match = None
                if possible_keys:
                    # Sort by length descending to get most specific key
                    possible_keys.sort(key=len, reverse=True)
                    best_match = possible_keys[0]
                
                if best_match:
                    # Add raw_name to variants
                    if 'variants' not in catalog[best_match] or catalog[best_match]['variants'] is None:
                        catalog[best_match]['variants'] = []
                    
                    if raw_name not in catalog[best_match]['variants']:
                        catalog[best_match]['variants'].append(raw_name)
                        # Sort variants for neatness? Or just append.
                        # print(f"  Mapped '{raw_name}' -> {best_match} (via '{rich_name}')")
                        updates_count += 1
                else:
                    pass
                    # print(f"  Could not map '{raw_name}' ({rich_name})")

        except Exception as e:
            print(f"Error reading {filename}: {e}")

    print(f"Saving {updates_count} new variants to YAML...")
    with open(YAML_PATH, 'w', encoding='utf-8') as f:
        yaml.dump(catalog, f)
    print("Done.")

if __name__ == "__main__":
    main()
