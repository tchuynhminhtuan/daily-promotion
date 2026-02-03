import yaml
import json
import re

MAPPING_FILE = "catalog/retailer_mapping.yaml"
MIGRATION_FILE = "catalog/key_migration_map.json"

def classify_variant(product_name, rule):
    """
    Decides which new key to map to based on strategy and keywords.
    rule = { "strategies": ["split_conn", "split_size"], "targets": { "tag1|tag2": new_key } }
    """
    strategies = rule["strategies"]
    targets = rule["targets"]
    p_lower = product_name.lower()
    
    # 1. Detect Conn
    conn_tag = "lower_tier" # default (wifi/gps)
    if "split_conn" in strategies:
        # Keywords for LTE/Cellular
        lte_keywords = ["5g", "cellular", "lte", "4g", "sim", "esim"]
        if any(kw in p_lower for kw in lte_keywords):
            conn_tag = "higher_tier"
    
    # 2. Detect Size
    size_tag = None
    if "split_size" in strategies:
        # We need to find which size matches
        # Iterate targets and extract the size component?
        # Targets keys are "conn_tag|size_tag"
        # Extract available sizes from tags
        available_sizes = set()
        for tag in targets.keys():
            parts = tag.split("|")
            if len(parts) > 1:
                available_sizes.add(parts[1])
                
        # Find match in string
        match_size = None
        for size in available_sizes:
            # size is like "41mm" or "12.9 inch"
            # Normalize for regex
            # "12.9 inch" -> "12[.,]9.*inch" key
            # "41mm" -> "41.*mm"
            
            # Simple check first
            s_clean = size.replace(".", "").replace(",", "").lower() # "129 inch"
            p_clean = p_lower.replace(".", "").replace(",", "")
            
            if size.lower() in p_lower:
                match_size = size
                break
                
            # Try removing space in size "12.9inch"
            size_nospace = size.lower().replace(" ", "")
            if size_nospace in p_lower:
                match_size = size
                break
            
            # Try regex for format
            # e.g. "41 mm" vs "41mm"
            if "mm" in size.lower():
                num = size.lower().replace("mm", "").strip()
                if re.search(rf"\b{num}\s*mm", p_lower):
                    match_size = size
                    break
            if "inch" in size.lower():
                num = size.lower().replace("inch", "").strip().replace(".", "[.,]")
                if re.search(rf"\b{num}\s*inch", p_lower):
                    match_size = size
                    break
                    
        size_tag = match_size
        
        # Fallback for Watches: if "Series 4" has 40/44 but no size specific?
        # Maybe use a default if only 2 sizes?
        # Or default to smaller?
        if not size_tag and "watch" in p_lower:
            # Check if 38/40/41/42 implies "lower" and 42/44/45/46/49 implies "higher"
            # Too risky. Return None
            pass

    # Construct Tag Key
    final_tag_parts = []
    if "split_conn" in strategies:
        final_tag_parts.append(conn_tag)
    if "split_size" in strategies:
        if size_tag:
             final_tag_parts.append(size_tag)
        else:
             # Size required but not found
             # Return None so we don't migrate (keep generic or warn)
             return None
             
    final_tag = "|".join(final_tag_parts)
    
    return targets.get(final_tag)

def fix_line(line, migration_map):
    if ":" not in line: return line
    parts = line.rsplit(":", 1)
    if len(parts) != 2: return line
    
    current_key = parts[1].strip()
    
    if current_key in migration_map:
        product_name = parts[0].strip()
        new_key = classify_variant(product_name, migration_map[current_key])
        
        if new_key:
            return f"{parts[0]}: {new_key}\n"
        else:
            # Could not determine variant.
            # Append TODO comment?
            # Or keep as is?
            # If we delete the key from Catalog, keeping it here breaks Reference integrity (Report will show it as Unmapped/Generic text).
            # Better to append comment
            return f"{line.rstrip()} # TODO: Ambiguous variant split\n"
            
    return line

def main():
    with open(MIGRATION_FILE, "r") as f:
        migration_map = json.load(f)
        
    with open(MAPPING_FILE, "r") as f:
        lines = f.readlines()
        
    new_lines = []
    fixed_count = 0
    ambiguous_count = 0
    
    for line in lines:
        processed = fix_line(line, migration_map)
        if processed != line:
            if "# TODO" in processed:
                ambiguous_count += 1
            else:
                fixed_count += 1
        new_lines.append(processed)
        
    with open(MAPPING_FILE, "w") as f:
        f.writelines(new_lines)
        
    print(f"Fixed {fixed_count} mappings. Found {ambiguous_count} ambiguous items.")

if __name__ == "__main__":
    main()
