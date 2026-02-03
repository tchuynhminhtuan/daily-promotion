import re
import sys

FILE = "catalog/retailer_mapping.yaml"

def unescape_yaml_key(line):
    return line

def fix_line(line):
    original = line
    # Strip comments? No, keep them.
    
    # Generic Keys to Fix
    targets = [
        "ipad_air_m2", "ipad_air_m3", 
        "ipad_pro_m4", "ipad_pro_m5",
        "macbook_air_m2", "macbook_air_m3", "macbook_air_m4",
        "macbook_pro_m4", "macbook_pro_m5",
        "apple_watch_series_11_aluminum"
    ]
    
    found_target = None
    for t in targets:
        if line.strip().endswith(f": {t}"):
            found_target = t
            break
            
    if not found_target:
        return line
        
    val = found_target
    new_val = val # Default
    
    lower_line = line.lower()
    
    # Logic
    if val == "ipad_air_m3":
        if "13" in lower_line: new_val = "ipad_air_13_inch_m3"
        elif "11" in lower_line: new_val = "ipad_air_11_inch_m3"
        
    elif val == "ipad_air_m2":
        if "13" in lower_line: new_val = "ipad_air_13_inch_m2"
        elif "11" in lower_line: new_val = "ipad_air_11_inch_m2"
        
    elif val == "ipad_pro_m5":
        if "13" in lower_line: new_val = "ipad_pro_13_inch_m5"
        elif "11" in lower_line: new_val = "ipad_pro_11_inch_m5"
        
    elif val == "ipad_pro_m4":
        if "13" in lower_line: new_val = "ipad_pro_13_inch_m4"
        elif "11" in lower_line: new_val = "ipad_pro_11_inch_m4"
        
    elif val == "macbook_air_m2":
         # Assume 13 if not specified? Or if 15 specified.
         if "15" in lower_line: new_val = "macbook_air_15_inch_m2"
         else: new_val = "macbook_air_13_inch_m2"
         
    elif val == "macbook_air_m3":
         if "15" in lower_line: new_val = "macbook_air_15_inch_m3"
         else: new_val = "macbook_air_13_inch_m3"
         
    elif val == "macbook_air_m4":
         if "15" in lower_line: new_val = "macbook_air_15_inch_m4"
         else: new_val = "macbook_air_13_inch_m4"
         
    elif val == "macbook_pro_m5":
         if "16" in lower_line: new_val = "macbook_pro_16_inch_m5"
         elif "14" in lower_line: new_val = "macbook_pro_14_inch_m5"
         
    elif val == "macbook_pro_m4":
         size = "14"
         if "16" in lower_line: size = "16"
         
         if "max" in lower_line:
             new_val = f"macbook_pro_{size}_inch_m4_max"
         elif "pro" in lower_line:
             new_val = f"macbook_pro_{size}_inch_m4_pro"
         else:
             new_val = f"macbook_pro_{size}_inch_m4"
             
    elif val == "apple_watch_series_11_aluminum":
        if "titan" in lower_line:
            new_val = "apple_watch_series_11_titanium"
        elif any(x in lower_line for x in ["cellular", "lte", "5g", "4g"]):
            new_val = "apple_watch_series_11_aluminum_lte"
        else:
             # Default to GPS if Aluminum? 
             # Or if ambiguous, stick to aluminum_gps?
             # Check if GPS is mentioned?
             # If just "Apple Watch Series 11 Aluminum", it's usually GPS.
             new_val = "apple_watch_series_11_aluminum_gps"
             
    if new_val != val:
        print(f"Fixing: {line.strip()} -> {new_val}")
        return line.replace(f": {val}", f": {new_val}")
        
    return line

lines = []
with open(FILE, "r") as f:
    lines = f.readlines()
    
new_lines = [fix_line(l) for l in lines]

with open(FILE, "w") as f:
    f.writelines(new_lines)
