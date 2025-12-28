
import json
from collections import defaultdict

MAPPINGS_FILE = "mappings_candidate.json"

def main():
    try:
        with open(MAPPINGS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ {MAPPINGS_FILE} not found!")
        return

    review_needed = data.get("_REVIEW_NEEDED_", [])
    mapped_count = len(data) - 1
    
    print(f"📊 Total Keys: {mapped_count}")
    print(f"⚠️  Review Needed: {len(review_needed)}")

    print("\n--- Spot Check: MacBook Air M4 (Formatting) ---")
    mba_m4_keys = sorted([k for k in data.keys() if "MacBook Air" in k and "M4" in k])
    for k in mba_m4_keys:
        if "(, " in k or ", )" in k or ", ," in k:
             print(f"❌ BAD FORMAT: {k}")
        else:
             print(f"✅ Key: {k}")
        print(f"   Sample: {data[k][:2]}")
        
    print("\n--- Spot Check: iPad Pro M4 (Granularity) ---")
    pro_m4_keys = sorted([k for k in data.keys() if "iPad Pro" in k and "M4" in k])
    for k in pro_m4_keys:
        print(f"✅ Key: {k}")

    print("\n--- Spot Check: iPad Mini 7 (Alias) ---")
    mini7_keys = sorted([k for k in data.keys() if "iPad mini (A17 Pro)" in k])
    for k in mini7_keys:
        print(f"✅ Key: {k}")

    print("\n--- Unmapped Review Items (First 10) ---")
    for item in review_needed[:10]:
        print(f"❌ {item}")

if __name__ == "__main__":
    main()
