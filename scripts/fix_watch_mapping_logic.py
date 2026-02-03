import yaml
import json
import re

MAPPING_FILE = "catalog/retailer_mapping.yaml"
RENORMALIZE_MAP_FILE = "catalog/watch_key_migration.json"

def main():
    with open(RENORMALIZE_MAP_FILE, "r") as f:
        renorm_map = json.load(f)
        
    with open(MAPPING_FILE, "r") as f:
        lines = f.readlines()
        
    new_lines = []
    
    # Pre-compiled regex for sizes
    re_42 = re.compile(r'\b42\s*mm', re.IGNORECASE)
    re_46 = re.compile(r'\b46\s*mm', re.IGNORECASE)
    
    for line in lines:
        if ":" not in line: 
            new_lines.append(line)
            continue
            
        parts = line.rsplit(":", 1)
        if len(parts) != 2: 
            new_lines.append(line)
            continue
            
        product_name = parts[0].strip()
        current_key = parts[1].strip()
        
        # 1. Apply Renormalization (Ugly Keys)
        if current_key in renorm_map:
            current_key = renorm_map[current_key]
            
        # 2. Apply Titan/Aluminum Logic for Series 10/11
        # Target: Series 10 or 11
        if "series 10" in product_name.lower() or "series 11" in product_name.lower():
            p_lower = product_name.lower()
            
            # Determine Material
            is_titan = "titan" in p_lower
            is_aluminum = "nhôm" in p_lower or "aluminum" in p_lower
            
            # Determine Conn
            is_lte = any(x in p_lower for x in ["5g", "lte", "cellular", "esim"])
            is_gps = "gps" in p_lower and not is_lte
            
            # Corrections:
            # Titan implies LTE
            if is_titan: 
                is_lte = True
                is_gps = False
                
            # GPS implies Aluminum (unless specific steel/ceramic logic exists, but user said GPS=Alu)
            if is_gps:
                is_aluminum = True
                
            # Determine Size
            size_suffix = ""
            if re_42.search(p_lower): size_suffix = "_42mm"
            elif re_46.search(p_lower): size_suffix = "_46mm"
            
            # Construct Target Key Base
            # Need to match catalog convention:
            # Aluminum: apple_watch_series_11_aluminum_gps_46mm or _lte_46mm
            # Titan: apple_watch_series_11_titanium_46mm (Implies LTE)
            
            series = "series_10" if "series 10" in p_lower else "series_11"
            
            # Try to construct key
            new_key_candidate = None
            
            if is_titan:
                # Titanium Key
                # If catalog has specific titanium key?
                # Assume standard naming: apple_watch_series_11_titanium_{size}
                if size_suffix:
                    new_key_candidate = f"apple_watch_{series}_titanium{size_suffix}"
            
            elif is_aluminum:
                # Aluminum Key
                conn_part = "_gps" if is_gps else "_lte" # Default to LTE if not specific? Or default GPS?
                # User didn't specify default for Aluminum if ambiguous.
                # If neither GPS nor LTE mentioned?
                # Usually Aluminum is GPS default.
                if not is_lte and not is_gps:
                     conn_part = "_gps"
                
                if size_suffix:
                    new_key_candidate = f"apple_watch_{series}_aluminum{conn_part}{size_suffix}"
                    
            if new_key_candidate:
                current_key = new_key_candidate
                
        # Write back
        new_lines.append(f"{parts[0]}: {current_key}\n")
        
    with open(MAPPING_FILE, "w") as f:
        f.writelines(new_lines)
        
    print("Fixed Watch Mappings.")

if __name__ == "__main__":
    main()
