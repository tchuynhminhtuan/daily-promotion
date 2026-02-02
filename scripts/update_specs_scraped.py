
import sqlite3

DB_PATH = "catalog/price_history.db"

# Data from Browser Subagent
SCRAPED_DATA = {
    "ipad_pro_m5": {
        "chip": "Apple M5 chip; 9-core or 10-core CPU, 10-core GPU, and 16-core Neural Engine",
        "display": "Ultra Retina XDR display (Tandem OLED), ProMotion technology, P3 wide color, True Tone",
        "back_camera": "12MP Wide camera, 4K video, ProRes"
    },
    "ipad_air_m3": {
        "chip": "Apple M3 chip; 8-core CPU, 9-core GPU, and 16-core Neural Engine",
        "display": "Liquid Retina display, P3 wide color, True Tone",
        "back_camera": "12MP Wide camera, 4K video"
    }
}

def update_specs():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("🚀 Updating Specs from Scraped Data...")
    
    for key, specs in SCRAPED_DATA.items():
        # Get Product ID (Check both exact key and potentially localized names if needed, but key is safest)
        cursor.execute("SELECT id FROM products WHERE key = ?", (key,))
        res = cursor.fetchone()
        
        if not res:
            print(f"⚠️ Product key NOT found: {key}. Inserting...")
            # Insert Product First
            name = specs.get('name') or key.replace("_", " ").title() # Fallback name
            if "m5" in key: name = "iPad Pro 11-inch (M5)"
            if "m3" in key: name = "iPad Air 11-inch (M3)"
            
            cursor.execute("INSERT INTO products (key, name, category, brand) VALUES (?, ?, ?, ?)", (key, name, "iPad", "Apple"))
            pid = cursor.lastrowid
        else:
            pid = res[0]
        
        # Upsert Specs
        cursor.execute("""
            INSERT INTO specs (product_id, chip, display, back_camera)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(product_id) DO UPDATE SET
                chip = excluded.chip,
                display = excluded.display,
                back_camera = excluded.back_camera
        """, (pid, specs['chip'], specs['display'], specs['back_camera']))
        
        print(f"✅ Updated {key}: Chip={specs['chip'][:30]}...")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    update_specs()
