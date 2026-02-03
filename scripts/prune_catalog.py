import re

FILE = "catalog/product_catalog.yaml"

blacklist = {
    "ipad_air_m2", "ipad_air_m3",
    "ipad_pro_m4", "ipad_pro_m5",
    "macbook_air_m2", "macbook_air_m3", "macbook_air_m4",
    "macbook_pro_m4", "macbook_pro_m5",
    "apple_watch_series_11_aluminum"
}

new_lines = []
skip = False

with open(FILE, "r") as f:
    for line in f:
        stripped = line.strip()
        is_indented = line.startswith(" ") or line.startswith("\t")
        is_comment = stripped.startswith("#")
        is_blank = not stripped
        
        # Handle Root Level Items
        if not is_indented and not is_comment and not is_blank:
            # Likely a key
            if ":" in line:
                key = line.split(":")[0].strip()
                if key in blacklist:
                    print(f"Pruning: {key}")
                    skip = True
                else:
                    skip = False
            else:
                # 0-indent but not key? weird error or multi-line string?
                # Assume keep
                skip = False
                
        # Decision
        if skip:
            continue
        else:
            new_lines.append(line)

with open(FILE, "w") as f:
    f.writelines(new_lines)
