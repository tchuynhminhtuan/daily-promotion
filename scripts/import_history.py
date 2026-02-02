
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
sys.path.append(str(BASE_DIR / "src"))

from processing.normalize import match_product_smart, normalize_text

DB_PATH = BASE_DIR / "catalog/price_history.db"
CATALOG_PATH = BASE_DIR / "catalog/product_catalog.yaml"
RAW_DIR = BASE_DIR / "data/raw"
LEGACY_DIR = BASE_DIR / "Market Promotion"

def load_catalog():
    with open(CATALOG_PATH, 'r') as f:
        return yaml.safe_load(f)

def load_all_csvs():
    all_rows = []
    
    # 1. New Data (data/raw/YYYY-MM-DD/file.csv)
    # Format: Semi-colon separated usually? Or allow pandas to sniff.
    # Actually based on analyze_price_trends.py, it's mostly ';' or ','
    
    files = list(RAW_DIR.rglob("*.csv")) + list(LEGACY_DIR.rglob("*.csv"))
    print(f"📂 Found {len(files)} CSV files. Reading...")
    
    for f in tqdm(files):
        try:
            # Try sniffing or common separators
            df = None
            for sep in [';', ',', '\t']:
                try:
                    df = pd.read_csv(f, sep=sep, on_bad_lines='skip', encoding='utf-8')

                    # Check columns
                    cols = [c.lower() for c in df.columns]
                    
                    has_name = any(x in cols for x in ['product_name', 'name', 'tên sản phẩm'])
                    has_price = any(x in cols for x in ['price', 'price_sale', 'gia_khuyen_mai', 'gia_niem_yet', 'giá'])
                    
                    if has_name and has_price:
                        break # Found correct separator
                    df = None
                except: continue
                
            if df is not None:
                # Normalize columns locally
                df.columns = [c.lower().strip() for c in df.columns]
                
                # Standardize
                
                # Identify columns
                name_col = next((c for c in df.columns if c in ['product_name', 'name', 'tên sản phẩm']), None)
                
                # Capture all potential price columns (prioritize later)
                price_cols = [c for c in df.columns if c in ['gia_khuyen_mai', 'price_sale', 'gia_niem_yet', 'price', 'giá']]
                
                if name_col and price_cols:
                    # Date Heuristic
                    date_str = "2023-01-01"
                    parent = f.parent.name
                    if re.match(r"202\d-\d{2}-\d{2}", parent):
                        date_str = parent
                    
                    # Convert to minimal dicts
                    # Keep name and ALL prices found
                    keep_cols = [name_col] + price_cols
                    batch = df[keep_cols].to_dict('records')
                    
                    for b in batch:
                        b['date'] = date_str
                        b['source'] = f.name
                        # Standardize key for main loop
                        b['_raw_name'] = b[name_col]
                        all_rows.append(b)
        except Exception as e:
            # print(f"Error reading {f}: {e}")
            pass
            

        

    return all_rows

def extract_variant(raw_name, product_key, catalog_data):
    """
    Strict Variant Verification.
    1. Check if 'storage' (128GB...) is in raw_name.
    2. Must match valid storage options for this product in catalog.
    3. Return canonical variant string or None (if invalid/ambiguous).
    """
    prod_info = catalog_data.get(product_key)
    if not prod_info: return None
    
    valid_storages = prod_info.get('storage', [])
    valid_colors = prod_info.get('colors', [])
    
    raw_norm = normalize_text(raw_name).upper() # 128gb -> 128GB
    
    # 1. Capacity Match
    found_cap = None
    for cap in valid_storages: # ["128GB", "256GB"]
        # Strict word boundary or check? " 128GB " or "128GB"
        # Since we normalized text, "128GB" might be "128 GB"
        # Regex is safer
        # Cap is usually "128GB". Regex: \b128\s*GB\b
        
        # Convert 1TB -> 1\s*TB
        numeric_part = re.match(r"(\d+)", cap).group(1)
        unit_part = cap.replace(numeric_part, "").strip() # GB or TB
        
        pattern = fr"\b{numeric_part}\s*{unit_part}\b"
        if re.search(pattern, raw_norm, re.IGNORECASE):
            if found_cap: 
                return None # Ambiguous (found 128GB AND 256GB?? Unlikely but safe)
            found_cap = cap
            
    # If Product HAS storage options but we found NONE -> Reject?
    # Yes, for price integrity. "iPhone 13" is ambiguous pricing. We want "iPhone 13 128GB".
    if valid_storages and not found_cap:
        return None
        
    return found_cap if found_cap else "Standard"

def detect_outliers(inserts):
    """
    Filter out price anomalies using Median Absolute Deviation (or simple Median ratio).
    Logic:
    1. Group by Product + Variant.
    2. Calc Median Price.
    3. Remove if Price < 0.3 * Median (70% off is suspicious) OR Price > 3 * Median (3x price is suspicious)
    """
    valid_data = []
    skipped = 0
    
    # Organize by key: (product_id, variant) -> [prices...]
    groups = {}
    for item in inserts:
        # item: (product_id, date, price, variant, source)
        key = (item[0], item[3])
        if key not in groups: groups[key] = []
        groups[key].append(item)
        
    print(f"📊 Analyzing {len(groups)} unique Product+Variant groups for outliers...")
    
    for key, items in tqdm(groups.items(), desc="Outlier Check"):
        prices = [x[2] for x in items]
        if not prices: continue
        
        median_price = sorted(prices)[len(prices)//2]
        
        # Thresholds
        lower_bound = median_price * 0.3 # < 30% of median (e.g. 5tr vs 15tr)
        upper_bound = median_price * 3.0 # > 300% of median
        
        for x in items:
            p = x[2]
            if lower_bound <= p <= upper_bound:
                valid_data.append(x)
            else:
                # print(f"⚠️ Outlier Rejected: {p:,} vs Median {median_price:,} (ID: {key[0]} {key[1]})")
                skipped += 1
                
    return valid_data, skipped

def import_history():
    print("🚀 Starting Historical Import...")
    
    # 1. Load Data
    rows = load_all_csvs()
    print(f"📊 Loaded {len(rows)} raw rows.")
    
    if len(rows) == 0:
        print("❌ No data found! Check load_all_csvs logic.")
        return
    
    catalog = load_catalog()
    
    # 2. Pre-load Candidates
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT p.key, p.name, p.category, s.chip, s.display, s.back_camera FROM products p LEFT JOIN specs s ON p.id = s.product_id")
    candidates = cursor.fetchall()
    
    key_to_id = {}
    cursor.execute("SELECT key, id FROM products")
    for r in cursor.fetchall():
        key_to_id[r['key']] = r['id']
    
    print("🧠 Smart Matching Logic Loaded.")
    
    raw_inserts = []
    skipped_ambiguous = 0
    
    # 3. Process Rows
    # 3. Process Rows
    for row in tqdm(rows, desc="Matching"):
        raw_name = str(row.get('_raw_name'))
        
        # Price Priority: Strict! Only Gia_Khuyen_Mai or Price_Sale
        # User Request: If missing, SKIP. Do not use Listed Price.
        price_raw = row.get('gia_khuyen_mai') or row.get('price_sale')
        
        if not price_raw or str(price_raw) == '0':
             skipped_ambiguous += 1
             continue
        
        try:
            p_str = str(price_raw)
            if '.' in p_str: p_str = p_str.split('.')[0] # 19.990.000 -> 19
            # Wait, clean all non-digits:
            p_clean = re.sub(r"[^\d]", "", p_str)
            if not p_clean: 
                skipped_ambiguous += 1
                continue
            price = int(p_clean)
            if price < 100000: # Junk < 100k
                skipped_ambiguous += 1
                continue
        except:
            skipped_ambiguous += 1
            continue
            
        matched_key = match_product_smart(raw_name, candidates=candidates)
        
        if matched_key:
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
