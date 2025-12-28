
import json
import re
from collections import Counter

DB_PATH = "apple_products_db.json"

def analyze():
    with open(DB_PATH) as f:
        data = json.load(f)
    
    spec_keys = Counter()
    
    print("--- Spec Keys by Family ---")
    family_specs = {} # {family: counter}
    
    for model, info in data.items():
        fam = info.get("Family", "Unknown")
        specs = info.get("Specs", {})
        
        if fam not in family_specs: family_specs[fam] = Counter()
        
        for k in specs.keys():
            family_specs[fam][k] += 1
            
    for fam, counter in family_specs.items():
        print(f"\n[{fam}]")
        for k, v in counter.most_common(5):
            print(f"  {k}: {v}")

    # Check content of potential variant keys
    print("\n--- Content Samples ---")
    for fam in ["iPhone", "iPad", "Apple Watch", "Mac"]:
        print(f"\n> {fam} Samples:")
        count = 0
        for model, info in data.items():
            if info.get("Family") == fam:
                specs = info.get("Specs", {})
                
                # Check Storage
                storage_keys = [k for k in specs if "Dung Lượng" in k or "Capacity" in k]
                if storage_keys:
                    print(f"  {model} -> Storage: {specs[storage_keys[0]]}")
                
                # Check Size (Watch)
                size_keys = [k for k in specs if "Kích Thước" in k or "Size" in k]
                if size_keys:
                    print(f"  {model} -> Size: {specs[size_keys[0]]}")
                
                count += 1
                if count > 2: break

if __name__ == "__main__":
    analyze()
