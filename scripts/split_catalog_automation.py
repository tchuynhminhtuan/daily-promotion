import yaml
import json
import re

CATALOG_FILE = "catalog/product_catalog.yaml"
MIGRATION_FILE = "catalog/key_migration_map.json"

def main():
    with open(CATALOG_FILE, "r") as f:
        data = yaml.safe_load(f)
        
    new_data = {}
    migration_map = {} # {old_key: {variant_type: {val: new_key}}}
    # Structure of migration_map needs to support logic:
    # "If old_key, check (conn/size) -> new_key"
    
    # We'll store a list of rules for the fixer script
    # rules = {old_key: { "strategies": ["split_conn", "split_size"], "targets": { "wifi": key_wifi, ... } } }
    
    deleted_keys = []
    
    for key, info in data.items():
        category = info.get("category")
        
        # Only process iPad and Watch
        if category not in ["iPad", "Watch"]:
            new_data[key] = info
            continue
            
        conn = info.get("connectivity") or []
        sizes = info.get("sizes") or []
        
        has_mixed_conn = len(conn) > 1
        has_mixed_sizes = len(sizes) > 1
        
        if not (has_mixed_conn or has_mixed_sizes):
            new_data[key] = info
            continue
            
        # Needs Splitting!
        print(f"Splitting {key} (Conn: {len(conn)}, Sizes: {len(sizes)})")
        deleted_keys.append(key)
        
        # We will generate a list of variant objects
        # Base variant is current info
        variants = [{"suffix": "", "name_suffix": "", "info": info.copy()}]
        
        # 1. Split by Connectivity (if mixed)
        if has_mixed_conn:
            # Assumes iPad style: Wi-Fi vs Wi-Fi + Cellular
            # Or Watch: GPS vs GPS + Cellular
            new_variants = []
            for v in variants:
                base_info = v["info"]
                
                # Create WiFi/GPS specific
                v1 = v.copy()
                v1["info"] = base_info.copy()
                
                if category == "iPad":
                    v1["suffix"] += "_wifi"
                    v1["name_suffix"] += " WiFi"
                    v1["info"]["connectivity"] = ["Wi-Fi"]
                    # Add keywords?
                    
                elif category == "Watch":
                    v1["suffix"] += "_gps"
                    v1["name_suffix"] += " (GPS)"
                    v1["info"]["connectivity"] = ["GPS"]
                
                new_variants.append(v1)
                
                # Create LTE/Cellular specific
                v2 = v.copy()
                v2["info"] = base_info.copy()
                
                if category == "iPad":
                    v2["suffix"] += "_lte"
                    v2["name_suffix"] += " 5G/LTE"
                    v2["info"]["connectivity"] = ["Wi-Fi + Cellular"]
                elif category == "Watch":
                    # Check if original key already had _lte? No, generic key.
                    v2["suffix"] += "_lte"
                    v2["name_suffix"] += " (GPS + Cellular)"
                    v2["info"]["connectivity"] = ["GPS + Cellular"]
                    
                new_variants.append(v2)
            
            variants = new_variants
            
        # 2. Split by Size (if mixed)
        # Note: iPads usually don't mix sizes in same key (except Air M2/Pro M4 which we fixed).
        # Scan found iPad Pro 9.7, 12.9... those are size specific keys.
        # But Watch keys mix sizes.
        
        if has_mixed_sizes:
            new_variants = []
            for v in variants:
                base_info = v["info"]
                # Iterate all sizes defined in catalog
                for size_str in sizes:
                    # Extract number
                    # "41mm" -> "41mm"
                    # "13 inch" -> "13_inch"
                    size_clean = size_str.replace(" ", "_").lower()
                    
                    v_size = v.copy()
                    v_size["info"] = base_info.copy()
                    v_size["suffix"] += f"_{size_clean}"
                    v_size["name_suffix"] += f" {size_str}"
                    v_size["info"]["sizes"] = [size_str]
                    
                    new_variants.append(v_size)
            variants = new_variants
            
        # Register new keys
        key_mapping_rule = {"strategies": [], "targets": {}}
        if has_mixed_conn: key_mapping_rule["strategies"].append("split_conn")
        if has_mixed_sizes: key_mapping_rule["strategies"].append("split_size")
        
        for v in variants:
            new_key = key + v["suffix"]
            new_info = v["info"]
            new_info["name"] = str(new_info["name"]) + v["name_suffix"]
            
            new_data[new_key] = new_info
            
            # Add to mapping rule
            # Identify "selector" for this variant
            # Combination of conn type and size
            
            # Tag: "wifi_41mm" or "lte_11_inch" etc.
            # We construct a composite tag to help the fixer script identify
            
            tag_parts = []
            if has_mixed_conn:
                if "wifi" in v["suffix"] or "gps" in v["suffix"] and "lte" not in v["suffix"]:
                    tag_parts.append("lower_tier") # wifi/gps
                else:
                    tag_parts.append("higher_tier") # lte/cellular
            
            if has_mixed_sizes:
                # Extract size from suffix
                # suffix might be "_gps_41mm" -> "41mm"
                # regex extract last part?
                # or just use the size_str we looped
                 # But we are iterating variants now.
                 # Let's rely on info['sizes'][0]
                 size_val = new_info['sizes'][0]
                 tag_parts.append(size_val)
                 
            tag = "|".join(tag_parts)
            key_mapping_rule["targets"][tag] = new_key
            
        migration_map[key] = key_mapping_rule

    # Save Catalog
    with open(CATALOG_FILE, "w") as f:
        yaml.dump(new_data, f, allow_unicode=True, sort_keys=False)
        
    # Save Migration Map
    with open(MIGRATION_FILE, "w") as f:
        json.dump(migration_map, f, indent=2)
        
    print(f"Split {len(deleted_keys)} keys into {len(new_data) - len(data) + len(deleted_keys)} new keys.")
    print(f"Migration map saved to {MIGRATION_FILE}")

if __name__ == "__main__":
    main()
