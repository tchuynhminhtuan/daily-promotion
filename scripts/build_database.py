"""
Build Analytics Database
Initializes `catalog/price_history.db` and imports:
1. Products & Specs from `apple_official_catalog.json`
2. Historical Price Data (Future step or included here)
"""
import sqlite3
import json
import os
from pathlib import Path
from datetime import datetime

DB_PATH = Path("catalog/price_history.db")
CATALOG_PATH = Path("catalog/apple_official_catalog.json")

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    category TEXT,
    brand TEXT DEFAULT 'Apple',
    url TEXT
);

CREATE TABLE IF NOT EXISTS specs (
    product_id INTEGER PRIMARY KEY,
    chip TEXT,
    display TEXT,
    back_camera TEXT,
    front_camera TEXT,
    battery TEXT,
    security TEXT,
    full_specs_json TEXT,
    FOREIGN KEY(product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    date DATE,
    retailer TEXT,
    price INTEGER,
    original_name TEXT,
    FOREIGN KEY(product_id) REFERENCES products(id)
);

CREATE INDEX IF NOT EXISTS idx_price_date ON price_history(date);
CREATE INDEX IF NOT EXISTS idx_price_product ON price_history(product_id);
"""

def init_db():
    if DB_PATH.exists():
        print(f"⚠️ Database {DB_PATH} already exists. Appending/Updating...")
    else:
        print(f"✨ Creating new database at {DB_PATH}")
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.executescript(SCHEMA)
    conn.commit()
    return conn

def import_catalog(conn):
    print("📦 Importing Catalog...")
    with open(CATALOG_PATH, 'r', encoding='utf-8') as f:
        catalog = json.load(f)
    
    cursor = conn.cursor()
    count = 0
    updated = 0
    
    for category, items in catalog.items():
        for item in items:
            # We need a unique key. 
            # The catalog currently has 'name', 'url', 'colors', 'storage'.
            # It DOES NOT have a 'key' field explicitly in the JSON I saw earlier (except 'model_key' from scraper? No, main catalog structure).
            # normalize.py generates keys like 'iphone_16_pro'.
            # We should generate a canonical key here or use one if it exists.
            
            # Let's generate a simple key from name if not present
            raw_name = item.get('name', 'Unknown')
            # normalize.py logic: lowercase, spaces to underscores
            # But wait, normalize.py usually maps TO these keys. 
            # Ideally the catalog should HAVE the keys.
            
            # Use 'model_key' from enrichment if available, OR generate one.
            # Enriched catalog has 'specs' -> 'model_key'?
            # Let's check enriched structure again.
            
            # Actually, `enrich_catalog.py` put `specs` inside the item.
            specs = item.get('specs', {})
            
            # Better key generation:
            slug = raw_name.lower().replace(' ', '_').replace('-', '_').replace('(', '').replace(')', '')
            # Remove special chars
            import re
            slug = re.sub(r'[^a-z0-9_]', '', slug)
            
            key = slug # e.g. iphone_16_pro
            
            # Upsert Product
            try:
                cursor.execute("""
                    INSERT INTO products (key, name, category, brand, url)
                    VALUES (?, ?, ?, 'Apple', ?)
                """, (key, raw_name, category, item.get('url')))
                product_id = cursor.lastrowid
                count += 1
            except sqlite3.IntegrityError:
                # Already exists, get ID
                cursor.execute("SELECT id FROM products WHERE key = ?", (key,))
                product_id = cursor.fetchone()[0]
                updated += 1

            # Insert Specs
            # Convert list fields to comma-separated string for simpler querying, or keep JSON
            full_specs = json.dumps(specs, ensure_ascii=False)
            
            # Helper to join list text
            def join_spec(k):
                val = specs.get(k)
                if isinstance(val, list):
                    return ' | '.join(val)
                return str(val) if val else None

            cursor.execute("""
                INSERT OR REPLACE INTO specs (product_id, chip, display, back_camera, front_camera, battery, security, full_specs_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                product_id,
                join_spec('chip'),
                join_spec('display'),
                join_spec('back_camera'),
                join_spec('front_camera'),
                join_spec('battery'),
                join_spec('security'),
                full_specs
            ))
            
    conn.commit()
    print(f"✅ Imported {count} new products from Catalog, Updated {updated}. Total: {count + updated}")

def import_scraped_specs_folder(conn):
    print("📂 Scanning 'catalog/specs/' for all historical products...")
    specs_dir = Path("catalog/specs")
    cursor = conn.cursor()
    
    count = 0
    
    # Iterate over all JSON files
    for json_file in specs_dir.glob("*/*.json"):
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Extract info
        name = data.get('device_name')
        if not name: continue
        
        category = data.get('_category', 'Unknown')
        
        # Make key
        slug = name.lower().replace(' ', '_').replace('-', '_').replace('(', '').replace(')', '')
        import re
        key = re.sub(r'[^a-z0-9_]', '', slug)
        
        # Insert Product (Ignore if exists)
        try:
            cursor.execute("""
                INSERT INTO products (key, name, category, brand)
                VALUES (?, ?, ?, 'Apple')
            """, (key, name, category))
            product_id = cursor.lastrowid
            count += 1
        except sqlite3.IntegrityError:
            cursor.execute("SELECT id FROM products WHERE key = ?", (key,))
            product_id = cursor.fetchone()[0]
        
        # Prepare Specs
        # We need to map raw keys to DB columns.
        # Prepare Specs
        # We need to map raw keys to DB columns.
        # We will use inline logic to map keys.
        # We can reuse the extraction logic if we import it, or just copy critical logic
        # Ideally reuse.
        
        # For this script let's just do a quick inline extraction or rely on raw json?
        # The table `specs` has specific columns: chip, display, etc.
        # Let's map them.
        
        # Simplified mapping (borrowed from enrichment script)
        MAPPING = {
            "Chip": "chip", "Màn Hình": "display", "Camera": "back_camera", 
            "Camera Sau": "back_camera", "Camera Trước": "front_camera", 
            "Pin": "battery", "Pin Và Nguồn Điện": "battery", 
            "Xác Thực": "security", "Bảo Mật": "security"
        }
        
        mapped_specs = {}
        for k, v in data.items():
            for map_k, map_col in MAPPING.items():
                if map_k in k:
                    # Join list to string
                    val_str = ' | '.join(v) if isinstance(v, list) else str(v)
                    mapped_specs[map_col] = val_str
                    break
        
        full_json = json.dumps(data, ensure_ascii=False)
        
        cursor.execute("""
            INSERT OR REPLACE INTO specs (product_id, chip, display, back_camera, front_camera, battery, security, full_specs_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            product_id,
            mapped_specs.get('chip'),
            mapped_specs.get('display'),
            mapped_specs.get('back_camera'),
            mapped_specs.get('front_camera'),
            mapped_specs.get('battery'),
            mapped_specs.get('security'),
            full_json
        ))
        
    conn.commit()
    print(f"✅ Processed {count} additional products from Specs folder.")

if __name__ == "__main__":
    conn = init_db()
    import_catalog(conn)
    import_scraped_specs_folder(conn)
    conn.close()
