FILE = "catalog/retailer_mapping.yaml"

def main():
    with open(FILE, "r") as f:
        lines = f.readlines()
        
    new_lines = []
    count = 0
    for line in lines:
        if "# TODO: Ambiguous variant split" in line:
            # Comment out the line
            if not line.strip().startswith("#"):
                new_lines.append("# [AMBIGUOUS] " + line)
                count += 1
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
            
    with open(FILE, "w") as f:
        f.writelines(new_lines)
        
    print(f"Disabled {count} ambiguous mappings.")

if __name__ == "__main__":
    main()
