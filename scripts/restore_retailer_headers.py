FILE = "catalog/retailer_mapping.yaml"

def main():
    with open(FILE, "r") as f:
        lines = f.readlines()
        
    new_lines = []
    restored = 0
    
    for line in lines:
        # Check for '# [INVALID KEY: ] retailer:' pattern
        if "# [INVALID KEY: ]" in line and ":" in line:
            # Check if value part is empty strings
            # e.g. "# [INVALID KEY: ] viettel_store:"
            
            # Clean string to check structure
            clean_part = line.replace("# [INVALID KEY: ]", "").strip()
            if clean_part.endswith(":"):
                # Ideally check if value is empty
                # "viettel_store:" -> parts=["viettel_store", ""]
                parts = clean_part.rsplit(":", 1)
                if len(parts) == 2 and not parts[1].strip():
                     # It's a header!
                     new_lines.append(clean_part + "\n")
                     restored += 1
                     continue
        
        new_lines.append(line)
        
    with open(FILE, "w") as f:
        f.writelines(new_lines)
    
    print(f"Restored {restored} retailer headers.")

if __name__ == "__main__":
    main()
