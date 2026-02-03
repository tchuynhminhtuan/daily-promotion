import sqlite3
import json
import yaml

DB_PATH = "catalog/price_history.db"
MIGRATION_FILE = "catalog/key_migration_map.json"

def main():
    try:
        with open(MIGRATION_FILE, "r") as f:
            migration_map = json.load(f)
            
        keys_to_delete = list(migration_map.keys())
        
        if not keys_to_delete:
            print("No keys to delete.")
            return

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        placeholders = ','.join('?' * len(keys_to_delete))
        
        # 1. Delete History linked to these products
        # Get IDs first
        query_ids = f"SELECT id, key FROM products WHERE key IN ({placeholders})"
        cursor.execute(query_ids, keys_to_delete)
        rows = cursor.fetchall()
        
        ids = [r[0] for r in rows]
        found_keys = [r[1] for r in rows]
        
        if ids:
            placeholders_ids = ','.join('?' * len(ids))
            
            # Delete prices
            q_del_prices = f"DELETE FROM price_history WHERE product_id IN ({placeholders_ids})"
            cursor.execute(q_del_prices, ids)
            rows_prices = cursor.rowcount
            print(f"Deleted {rows_prices} timestamped price records.")
            
            # Delete products
            q_del_prods = f"DELETE FROM products WHERE id IN ({placeholders_ids})"
            cursor.execute(q_del_prods, ids)
            rows_prods = cursor.rowcount
            print(f"Deleted {rows_prods} product keys from DB.")
            
        else:
            print("No matching keys found in DB (already clean?).")
            
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
