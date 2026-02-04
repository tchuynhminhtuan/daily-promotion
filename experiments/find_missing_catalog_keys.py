
import yaml
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CATALOG_PATH = BASE_DIR / "catalog/product_catalog.yaml"
# Using the fixed CSV as the source of "intended" keys
CSV_PATH = BASE_DIR / "experiments/manual-fixed-2026-02-03.csv"
OUTPUT_FILE = BASE_DIR / "experiments/missing_catalog_entries.txt"

def main():
    print(f"🔍 Checking for keys in {CSV_PATH.name} missing from product_catalog.yaml...")

    # 1. Load Catalog Keys
    try:
        with open(CATALOG_PATH, 'r') as f:
            catalog = yaml.safe_load(f) or {}
            catalog_keys = set(catalog.keys())
            print(f"✅ Loaded {len(catalog_keys)} keys from Catalog.")
    except Exception as e:
        print(f"❌ Error loading catalog: {e}")
        return

    # 2. Load Mapped Keys from CSV
    try:
        # Try semicolon first (common in this project)
        try:
            df = pd.read_csv(CSV_PATH, sep=';', on_bad_lines='skip')
        except:
            df = pd.read_csv(CSV_PATH, sep=',', on_bad_lines='skip')
            
        if 'mapped' not in df.columns:
            print("❌ Column 'mapped' not found in CSV.")
            return

        csv_keys = set(df['mapped'].dropna().unique())
        print(f"✅ Found {len(csv_keys)} unique mapped keys in CSV.")
        
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        return

    # 3. Find Missing
    missing = [k for k in csv_keys if k not in catalog_keys and k.lower() != "none" and k.lower() != "ignore"]
    
    if not missing:
        print("🎉 All mapped keys are present in the catalog!")
    else:
        print(f"⚠️ Found {len(missing)} keys missing from catalog:")
        missing.sort()
        
        with open(OUTPUT_FILE, 'w') as f:
            for k in missing:
                print(f" - {k}")
                f.write(f"{k}\n")
        
        print(f"\n📝 List saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
