import re
import yaml

FILE = "catalog/retailer_mapping.yaml"

def analyze_ipad_mini_variant(name):
    """
    Returns 'lte' or 'wifi' based on namestring.
    Default to 'wifi' if ambiguous? 
    Usually 5G models have specific keywords.
    """
    n = name.lower()
    if '5g' in n or 'cellular' in n or 'lte' in n or '4g' in n:
        return 'lte'
    return 'wifi'

def fix_line(line):
    # Only target lines with ipad_mini_a17_pro mapping
    target_key = "ipad_mini_a17_pro"
    
    if f": {target_key}" not in line: 
        return line
    
    # Extract product name (Key in YAML)
    # Format: "  Product Name: key"
    # Split by last colon
    parts = line.rsplit(":", 1)
    if len(parts) != 2: return line
    
    product_name_part = parts[0].strip()
    # Remove leading spaces or quotes if needed, but simple analysis works on string
    
    variant = analyze_ipad_mini_variant(product_name_part)
    
    new_key = f"{target_key}_{variant}"
    
    # Replace content
    # Use rsplit to replace only the value part
    new_line = f"{parts[0]}: {new_key}\n"
    
    print(f"Fixed: {product_name_part} -> {new_key}")
    return new_line

with open(FILE, "r") as f:
    lines = f.readlines()
    
new_lines = [fix_line(l) for l in lines]

with open(FILE, "w") as f:
    f.writelines(new_lines)
