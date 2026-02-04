
import sqlite3
import pandas as pd
import sys
import yaml
import re
from pathlib import Path
from tqdm import tqdm

# Add src to path
BASE_DIR = Path(__file__).parent.parent
sys.path.append(str(BASE_DIR))

from src.matching.engine import match_product
from src.utils.cleaner import normalize_text, normalize_storage, clean_price
from src.utils.config import load_catalog

DB_PATH = BASE_DIR / "catalog/price_history.db"
CATALOG_PATH = BASE_DIR / "catalog/product_catalog.yaml"
RAW_DIR = BASE_DIR / "data/raw"
LEGACY_DIR = BASE_DIR / "data/legacy_source/Market Promotion"

def load_catalog():
    with open(CATALOG_PATH, 'r') as f:
        return yaml.safe_load(f)

# ... (skip load_all_csvs) ...

def import_history():
    print("🚀 Starting Historical Import...")
    
    # 1. Load Data
    rows = load_all_csvs()
    print(f"📊 Loaded {len(rows)} raw rows.")
    
    if len(rows) == 0:
        print("❌ No data found! Check load_all_csvs logic.")
        return
    
    catalog = load_catalog()
    
    # 2. Database Connection
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    key_to_id = {}
    # Use try-except in case table is empty or products missing
    try:
        cursor.execute("SELECT key, id FROM products")
        for r in cursor.fetchall():
            key_to_id[r['key']] = r['id']
    except:
        pass
    
    print("🧠 Smart Matching Logic Loaded.")
    
    raw_inserts = []
    skipped_ambiguous = 0
    
    # 3. Process Rows
    for row in tqdm(rows, desc="Matching"):
        raw_name = str(row.get('_raw_name'))
        
        # Price Priority
        price_raw = row.get('gia_khuyen_mai') or row.get('price_sale')
        
        if not price_raw or str(price_raw) == '0':
             skipped_ambiguous += 1
             continue
        
        try:
            price = clean_price(price_raw)
            if not price or price < 100000:
                skipped_ambiguous += 1
                continue
        except:
            skipped_ambiguous += 1
            continue
            
        # Refactored Match: Use src.matching.engine
        matched_key, _ = match_product(raw_name, "", catalog)
        
        if matched_key:
            # Check if key exists in DB (products table)
            if matched_key not in key_to_id:
                 # Ensure we only insert valid FKs
                 skipped_ambiguous += 1
                 continue
                 
            variant = extract_variant(raw_name, matched_key, catalog)
            if variant:
                raw_inserts.append((
                    key_to_id[matched_key],
                    row['date'],
                    price,
                    variant,
                    row['source']
                ))
            else:
                skipped_ambiguous += 1
        else:
            skipped_ambiguous += 1
            
    print(f"🔍 Matched {len(raw_inserts)} potential records. (Skipped {skipped_ambiguous} ambiguous)")
    
    # 4. Outlier Detection
    valid_inserts, skipped_outliers = detect_outliers(raw_inserts)
    print(f"✅ Final Valid Records: {len(valid_inserts)} (Removed {skipped_outliers} outliers)")
    
    # 5. Insert
    cursor.execute("BEGIN TRANSACTION")
    try:
        # Clear old legacy data? Or just append?
        # User implies "import historical", maybe we should wipe 'prices' first or use CREATE TABLE IF NOT EXISTS?
        # Assuming append is safer, but idempotency...
        # Let's delete existing data from SOURCE if we want to re-run? 
        # For now, just INSERT.
        
        cursor.executemany("""
            INSERT INTO price_history (product_id, date, price, variant, source)
            VALUES (?, ?, ?, ?, ?)
        """, valid_inserts)
        conn.commit()
        print("💾 Database Updated Successfully!")
    except Exception as e:
        conn.rollback()
        print(f"❌ Error importing: {e}")
        
    conn.close()

if __name__ == "__main__":
    import_history()
