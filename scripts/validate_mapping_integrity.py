import yaml
import sys

MAPPING_FILE = "catalog/retailer_mapping.yaml"
CATALOG_FILE = "catalog/product_catalog.yaml"

def main():
    # Load Catalog Keys
    with open(CATALOG_FILE, "r") as f:
        catalog = yaml.safe_load(f)
    valid_keys = set(catalog.keys())
    
    # Process Mapping File line by line to preserve comments/structure
    with open(MAPPING_FILE, "r") as f:
        lines = f.readlines()
        
    new_lines = []
    disabled_count = 0
    
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue
            
        if ":" not in line:
            new_lines.append(line)
            continue
            
        # Parse key
        # Format: "  Product Name: key"
        parts = line.rsplit(":", 1)
        if len(parts) != 2:
            new_lines.append(line)
            continue
            
        key_val = parts[1].strip()
        
        # Check if key is special (nan, ignore lists?)
        if key_val == "nan" or key_val in ["ip_address", "maple_leaf_chrysanthemum", "student"]: 
             new_lines.append(line)
             continue
             
        # Check against catalog
        if key_val not in valid_keys:
            # INVALID!
            # Comment out
            new_lines.append(f"# [INVALID KEY: {key_val}] {line.lstrip()}")
            disabled_count += 1
        else:
            new_lines.append(line)
            
    with open(MAPPING_FILE, "w") as f:
        f.writelines(new_lines)
        
    print(f"Validation Complete. Disabled {disabled_count} invalid mappings.")

if __name__ == "__main__":
    main()
