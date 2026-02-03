import yaml
import re

CATALOG_FILE = "catalog/product_catalog.yaml"
MIGRATION_FILE = "catalog/watch_key_migration.json"
import json

def clean_key(key):
    # Fix double suffixes
    new_key = key
    new_key = new_key.replace("_lte_lte", "_lte")
    new_key = new_key.replace("_gps_gps", "_gps")
    new_key = new_key.replace("_lte_gps", "_gps") # Priority to last split (GPS)
    new_key = new_key.replace("_gps_lte", "_lte") # Priority to last split (LTE)
    return new_key

def main():
    with open(CATALOG_FILE, "r") as f:
        data = yaml.safe_load(f)
        
    new_data = {}
    migration_map = {} # old -> new
    
    for key, info in data.items():
        if "apple_watch" not in key:
            new_data[key] = info
            continue
            
        cleaned_key = clean_key(key)
        
        # Also clean Name if needed
        # "Apple Watch ... (GPS + Cellular) (GPS + Cellular)"
        name = info.get("name", "")
        name = name.replace("(GPS + Cellular) (GPS + Cellular)", "(GPS + Cellular)")
        name = name.replace("(GPS) (GPS)", "(GPS)")
        name = name.replace("(GPS + Cellular) (GPS)", "(GPS)")
        name = name.replace("(GPS) (GPS + Cellular)", "(GPS + Cellular)")
        
        info["name"] = name
        
        new_data[cleaned_key] = info
        
        if key != cleaned_key:
            migration_map[key] = cleaned_key
            print(f"Renamed: {key} -> {cleaned_key}")
            
    with open(CATALOG_FILE, "w") as f:
        yaml.dump(new_data, f, allow_unicode=True, sort_keys=False)
        
    with open(MIGRATION_FILE, "w") as f:
        json.dump(migration_map, f, indent=2)

if __name__ == "__main__":
    main()
