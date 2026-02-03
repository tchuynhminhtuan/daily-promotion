import re
import sys

FILE = "catalog/retailer_mapping.yaml"

def fix_line(line):
    # Only target lines with macbook_pro mapping
    if "macbook_pro" not in line: return line
    
    # Check what size the Product Name implies
    # "MacBook Pro 14" or "MacBook Pro 16"
    
    # Regex for Size in Name
    is_14 = re.search(r"Pro\s?14\b", line, re.IGNORECASE)
    is_16 = re.search(r"Pro\s?16\b", line, re.IGNORECASE)
    
    if not (is_14 or is_16):
        # Ambiguous or neither (e.g. just MacBook Pro M2)?
        return line
        
    current_val_14 = "14_inch" in line
    current_val_16 = "16_inch" in line
    
    if is_14 and current_val_16:
        # Correct 16 -> 14
        print(f"Correcting 16->14: {line.strip()}")
        return line.replace("16_inch", "14_inch")
        
    if is_16 and current_val_14:
        # Correct 14 -> 16
        print(f"Correcting 14->16: {line.strip()}")
        return line.replace("14_inch", "16_inch")
        
    return line

with open(FILE, "r") as f:
    lines = f.readlines()
    
new_lines = [fix_line(l) for l in lines]

with open(FILE, "w") as f:
    f.writelines(new_lines)
