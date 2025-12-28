
import json
import shutil

DB_FILE = "apple_products_db.json"
BACKUP_FILE = "apple_products_db.json.bak"

def patch_families():
    print(f"🔧 Patching Families in {DB_FILE} with Strict Rules...")
    
    # Backup
    shutil.copy(DB_FILE, BACKUP_FILE)
    
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    count = 0
    for key, item in data.items():
        original_family = item.get("Family", "Unknown")
        name = item.get("Model", key)
        
        # Default: keep what we have, but we will force overwrite based on name
        new_family = original_family
        
        # Strict Rules (Order matters slightly, but usually distinct)
        if "iPhone" in name:
            new_family = "iPhone"
        elif "iPad" in name:
            new_family = "iPad"
        elif "MacBook" in name or "iMac" in name or "Mac mini" in name or "Mac Studio" in name or "Mac Pro" in name:
            new_family = "Mac"
        elif "AirPods" in name:
            new_family = "AirPods"
        elif "Apple Watch" in name:
            new_family = "Apple Watch"
        elif "Apple TV" in name:
            new_family = "Apple TV"
        elif "Display" in name or "Pro Display" in name:
            new_family = "Display"
        elif "HomePod" in name:
            new_family = "HomePod"
        elif "iPod" in name:
            new_family = "iPod"
        elif "Beats" in name:
            new_family = "Beats"
            
        # Apply Update
        if new_family != original_family:
            print(f"  Fixed: {name} | {original_family} -> {new_family}")
            item["Family"] = new_family
            count += 1
            
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    print(f"✅ Patched {count} items.")

if __name__ == "__main__":
    patch_families()
