
import sqlite3
import json
import os
import glob
import csv
import re

DB_FILE = "apple_prices.db"
PRODUCTS_JSON = "apple_products_db.json"
MAPPINGS_JSON = "mappings_candidate.json"

def init_db():
    """Initialize Database Tables."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Products Table (Official Specs)
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_key TEXT UNIQUE NOT NULL,
            family TEXT,
            specs TEXT, -- JSON stored as string
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Mappings Table (Raw Input -> Normalized Key)
    c.execute('''
        CREATE TABLE IF NOT EXISTS mappings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            raw_name TEXT UNIQUE NOT NULL,
            normalized_key TEXT,
            product_id INTEGER, -- FK to products.id (Nullable)
            confidence REAL DEFAULT 1.0,
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    ''')
    
    # Prices Table (Daily Scrapes)
    c.execute('''
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER, -- FK to products.id (via mapping)
            retailer TEXT,
            date DATE,
            price INTEGER,
            original_price INTEGER,
            currency TEXT DEFAULT 'VND',
            in_stock BOOLEAN,
            color TEXT,
            raw_name TEXT,
            url TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    ''')
    
    conn.commit()
    return conn

def import_products(conn):
    """Load apple_products_db.json into products table."""
    try:
        with open(PRODUCTS_JSON, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ {PRODUCTS_JSON} not found. Skipping products import.")
        return

    c = conn.cursor()
    count = 0
    updated = 0
    
    print(f"📦 Importing {len(data)} products...")
    
    for model_name, details in data.items():
        family = details.get("Family", "Unknown")
        specs_json = json.dumps(details, ensure_ascii=False)
        
        # Upsert Logic
        try:
            c.execute('''
                INSERT INTO products (model_key, family, specs)
                VALUES (?, ?, ?)
                ON CONFLICT(model_key) DO UPDATE SET
                specs = excluded.specs,
                family = excluded.family
            ''', (model_name, family, specs_json))
            count += 1
        except sqlite3.Error as e:
            print(f"  Error importing {model_name}: {e}")
            
    conn.commit()
    print(f"✅ Imported/Updated {count} products.")

def import_mappings(conn):
    """Load mappings_candidate.json into mappings table."""
    try:
        with open(MAPPINGS_JSON, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ {MAPPINGS_JSON} not found. Skipping mappings import.")
        return

    c = conn.cursor()
    count = 0
    
    # Build Product Lookup Cache (Model Key -> ID)
    c.execute("SELECT model_key, id FROM products")
    product_map = {row[0]: row[1] for row in c.fetchall()}
    
    # Special entries to skip
    skip_keys = ["_REVIEW_NEEDED_", "_METADATA_"]
    
    print(f"🔗 Importing mappings from {len(data)} normalized keys...")
    
    for norm_key, raw_list in data.items():
        if norm_key in skip_keys: continue
        
        # Link to Product ID if possible
        # 1. Exact Match
        pid = product_map.get(norm_key)
        
        # 2. Heuristic: If norm_key is "iPad Pro (M4)" and we can't match exact, we leave NULL.
        # This is expected behavior for Bridge Keys.
        
        for raw_name in raw_list:
            try:
                c.execute('''
                    INSERT INTO mappings (raw_name, normalized_key, product_id)
                    VALUES (?, ?, ?)
                    ON CONFLICT(raw_name) DO UPDATE SET
                    normalized_key = excluded.normalized_key,
                    product_id = excluded.product_id
                ''', (raw_name, norm_key, pid))
                count += 1
            except sqlite3.Error as e:
                # Typically duplicate raw_name if file has dupes (shouldn't happen with valid normalization)
                print(f"  Error mapping '{raw_name}': {e}")

    conn.commit()
    print(f"✅ Imported/Updated {count} mappings.")

def clean_price(price_str):
    """Convert '24.990.000 ₫' to 24990000."""
    if not price_str: return None
    # Remove non-digits
    digits = re.sub(r'[^\d]', '', price_str)
    if not digits: return None
    return int(digits)

def parse_retailer_from_filename(filename):
    """Extract 'fpt' from '1-fpt-2025-12-27.csv'."""
    # Pattern: Digit-Retailer-Date
    match = re.search(r'^\d+-([a-zA-Z0-9]+)-', filename)
    if match: return match.group(1).lower()
    return "unknown"

def import_prices(conn):
    """Scan content/ folder and ingest all CSV prices."""
    c = conn.cursor()
    
    # 1. Build Mapping Cache (Raw Name -> Product ID)
    # We join mappings -> products to get the direct Product ID
    print("🧠 Building Mapping Cache...")
    c.execute("SELECT raw_name, product_id FROM mappings")
    mapping_cache = {row[0]: row[1] for row in c.fetchall()}
    
    # 2. Find CSVs
    csv_files = glob.glob("content/**/*.csv", recursive=True)
    print(f"📂 Found {len(csv_files)} CSV files to process.")
    
    count = 0
    skipped = 0
    
    for file_path in csv_files:
        filename = os.path.basename(file_path)
        retailer = parse_retailer_from_filename(filename)
        
        # Read CSV
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Use semi-colon delimiter as seen in file content
                reader = csv.DictReader(f, delimiter=';')
                
                rows_to_insert = []
                for row in reader:
                    raw_name = row.get("Product_Name", "").strip()
                    if not raw_name: continue
                    
                    # Logic: 
                    # 1. Get Product ID from Cache
                    pid = mapping_cache.get(raw_name)
                    # If None, it means either unmapped OR mapped to a key but that key has no product_id?
                    # Actually mapping_cache stores `product_id`. If `mappings` has it null, we get None.
                    
                    price_sale = clean_price(row.get("Gia_Khuyen_Mai"))
                    price_list = clean_price(row.get("Gia_Niem_Yet"))
                    
                    # Date from row, fallback to file/folder date could be added if needed
                    date_str = row.get("Date", "").strip() 
                    
                    in_stock_str = row.get("Ton_Kho", "").lower()
                    in_stock = 1 if in_stock_str in ["yes", "co", "có", "true"] else 0
                    
                    color = row.get("Color", "").strip()
                    url = row.get("Link", "").strip()
                    
                    rows_to_insert.append((
                        pid, retailer, date_str, price_sale, price_list, in_stock, color, raw_name, url
                    ))
                
                # Batch Insert
                if rows_to_insert:
                    c.executemany('''
                        INSERT INTO prices (product_id, retailer, date, price, original_price, in_stock, color, raw_name, url)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', rows_to_insert)
                    count += len(rows_to_insert)
                    
        except Exception as e:
            print(f"❌ Error reading {filename}: {e}")
            skipped += 1
            
    conn.commit()
    print(f"✅ Imported {count} price records from {len(csv_files)} files.")

def verify_db(conn):
    """Run sanity checks."""
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM products")
    p_count = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM mappings")
    m_count = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM prices")
    price_count = c.fetchone()[0]
    
    print("\n--- Database Stats ---")
    print(f"Products: {p_count}")
    print(f"Mappings: {m_count}")
    print(f"Prices:   {price_count}")
    
    # Sample Price Check
    print("\n--- Sample Prices ---")
    c.execute('''
        SELECT date, retailer, m.normalized_key, price 
        FROM prices pr
        JOIN mappings m ON pr.raw_name = m.raw_name
        WHERE price > 0 
        ORDER BY date DESC 
        LIMIT 5
    ''')
    for row in c.fetchall():
        print(row)

if __name__ == "__main__":
    conn = init_db()
    import_products(conn)
    import_mappings(conn)
    import_prices(conn)
    verify_db(conn)
    conn.close()
