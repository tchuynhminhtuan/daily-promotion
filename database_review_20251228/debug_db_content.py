
import sqlite3
import pandas as pd

DB_FILE = "apple_prices.db"

def debug_product(model_name):
    print(f"🔍 Debugging: '{model_name}'")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # 1. Check Product
    print("\n--- 1. Product Table ---")
    c.execute("SELECT id, model_key, family FROM products WHERE model_key = ?", (model_name,))
    product = c.fetchone()
    if not product:
        print("❌ Product NOT FOUND in `products` table.")
        conn.close()
        return
    
    pid, key, family = product
    print(f"✅ Found: ID={pid}, Key='{key}', Family='{family}'")
    
    # 2. Check Mappings
    print("\n--- 2. Mappings Table ---")
    c.execute("SELECT count(*), count(product_id) FROM mappings WHERE normalized_key = ?", (model_name,))
    total_maps, linked_maps = c.fetchone()
    print(f"Total Mappings for this key: {total_maps}")
    print(f"Mappings with valid product_id: {linked_maps}")
    
    c.execute("SELECT raw_name, product_id FROM mappings WHERE normalized_key = ? LIMIT 5", (model_name,))
    for row in c.fetchall():
        print(f"   - '{row[0]}' -> pid={row[1]}")
        
    # 3. Check Prices
    print("\n--- 3. Prices Table ---")
    c.execute("SELECT count(*) FROM prices WHERE product_id = ?", (pid,))
    price_count = c.fetchone()[0]
    print(f"Prices linked to Product ID {pid}: {price_count}")
    
    if price_count == 0:
        print("\n❌ NO PRICES LINKED! Checking if prices exist for valid raw names but missed ID...")
        c.execute("SELECT raw_name FROM mappings WHERE normalized_key = ? LIMIT 1", (model_name,))
        sample_raw = c.fetchone()
        if sample_raw:
            raw = sample_raw[0]
            c.execute("SELECT count(*) FROM prices WHERE raw_name = ?", (raw,))
            count_by_raw = c.fetchone()[0]
            print(f"   Note: There are {count_by_raw} price rows for raw name '{raw}'")
            if count_by_raw > 0:
                print("   ➡️  CONCLUSION: Prices exist but `product_id` column in `prices` table is NULL.")
    
    conn.close()

if __name__ == "__main__":
    debug_product("AirPods (thế hệ thứ 2)")
