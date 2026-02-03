import yaml
import re

CATALOG_FILE = "catalog/product_catalog.yaml"

def main():
    with open(CATALOG_FILE, "r") as f:
        data = yaml.safe_load(f)
        
    keys_to_remove = []
    keys_to_add = {}
    
    # Define standardization logic
    for key, info in data.items():
        p_name = info.get("name", "").lower()
        
        # 1. Clean "Ugly" suffixes
        if "_lte_gps" in key or "_lte_lte" in key or "_lte_wifi" in key:
            keys_to_remove.append(key)
            continue
            
        # 2. Series 11 Standardization
        if "apple_watch_series_11" in key:
            # Check Material
            is_titan = "titan" in p_name or "titan" in key
            is_alum = not is_titan # Default to Aluminum per rule
            
            # Extract Size
            size = None
            if "42mm" in key or "42mm" in info.get("sizes", []): size = "42mm"
            if "46mm" in key or "46mm" in info.get("sizes", []): size = "46mm"
            
            if not size: continue # Skip generic keys without size
            
            # Create Standard Keys
            if is_titan:
                # Rule: Single Key per Size for Titan
                std_key = f"apple_watch_series_11_titanium_{size}"
                if std_key not in data and std_key not in keys_to_add:
                    new_info = info.copy()
                    new_info["name"] = f"Apple Watch Series 11 (Titanium) {size}"
                    new_info["connectivity"] = ["GPS + Cellular"]
                    keys_to_add[std_key] = new_info
                    
                # Mark current key for removal if it doesn't match std_key
                if key != std_key:
                    keys_to_remove.append(key)
                    
            elif is_alum:
                # Rule: Two Keys (GPS, LTE) per Size
                # Check what type current key is
                is_gps = "_gps" in key or "gps" in p_name
                is_lte = "_lte" in key or "cellular" in p_name or "5g" in p_name
                
                # If explicit GPS or LTE, rename to standard
                target_suffix = ""
                if is_gps and not is_lte: target_suffix = "_gps"
                elif is_lte: target_suffix = "_lte"
                else: 
                     # Ambiguous alum key? Make both?
                     # Let's assume we map explicitly found keys to their standard counterpart
                     continue
                
                std_key = f"apple_watch_series_11_aluminum{target_suffix}_{size}"
                
                if std_key not in data and std_key not in keys_to_add:
                    new_info = info.copy()
                    suffix_name = "(GPS)" if target_suffix == "_gps" else "(GPS + Cellular)"
                    new_info["name"] = f"Apple Watch Series 11 (Nhôm) {suffix_name} {size}"
                    new_info["connectivity"] = ["GPS"] if target_suffix == "_gps" else ["GPS + Cellular"]
                    keys_to_add[std_key] = new_info
                    
                if key != std_key:
                    keys_to_remove.append(key)

        # 3. iPad A16 Standardization
        if "ipad_a16" in key:
            # iPad A16 should imply 2 variants: Wifi, LTE
            # Current keys: ipad_a16_wifi, ipad_a16_lte_wifi, ipad_a16_lte_lte
            
            # We want: ipad_a16_wifi, ipad_a16_lte
            
            if "_lte_wifi" in key:
                keys_to_remove.append(key)
                
            elif "_lte_lte" in key:
                # Rename to _lte
                std_key = "ipad_a16_lte"
                keys_to_add[std_key] = info.copy()
                keys_to_add[std_key]["name"] = "iPad A16 5G/LTE"
                keys_to_add[std_key]["connectivity"] = ["Wi-Fi + Cellular"]
                keys_to_remove.append(key)
                
            elif key == "ipad_a16_wifi":
                # Ensure it's correct
                info["name"] = "iPad A16 WiFi"
                info["connectivity"] = ["Wi-Fi"]
                # Keep it
                
    # Execute Updates
    for k in keys_to_remove:
        if k in data:
            del data[k]
            
    data.update(keys_to_add)
    
    with open(CATALOG_FILE, "w") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False)
        
    print(f"Removed {len(keys_to_remove)} keys.")
    print(f"Added {len(keys_to_add)} standardized keys.")
    print("Catalog standardized per user rules.")

if __name__ == "__main__":
    main()
