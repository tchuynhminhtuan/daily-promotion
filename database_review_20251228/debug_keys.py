import json
import re

DB_FILE = "apple_products_db.json"

def clean_string(text):
    text = text.lower()
    for w in ["inch", "gen", "(", ")", ",", "-"]:
        text = text.replace(w, " ")
    text = re.sub(r'[^\w\s]', ' ', text)
    return " ".join(text.split())

def main():
    with open(DB_FILE, 'r') as f:
        data = json.load(f)
        
    keys = list(data.keys())
    print(f"Loaded {len(keys)} keys.\n")
    
    # Filter for iPad Pro
    pro_keys = [k for k in keys if "iPad Pro" in k]
    print("--- Existing iPad Pro Keys ---")
    for k in pro_keys[:10]:
        print(f"Original: {k}")
        print(f"Cleaned:  {clean_string(k)}")
        
    print("\n--- Testing Bridge Key Generation ---")
    bridge_keys = set()
    for k in keys:
        # Strategy: Remove size patterns like "11-inch", "13-inch", "14-inch"
        # Regex: \d+(\.\d+)?(-|\s)?inch
        
        # We work on the original key
        # Remove " (M4)" type stuff? No keep chip.
        # Remove " 11-inch"
        
        # Pattern: (11|13|14|15|16|24|27)(-|\s)?inch
        start = k
        reduced = re.sub(r'\b(1[0-9]|2[0-9])(-|\s)?inch\b', '', k, flags=re.IGNORECASE)
        reduced = re.sub(r'\b(1[0-9]|2[0-9])\.\d+(-|\s)?inch\b', '', reduced, flags=re.IGNORECASE) # For 10.9 inch
        
        # Clean
        reduced = reduced.replace("  ", " ").strip()
        
        # Remove parens and commas for final look
        clean_reduced = clean_string(reduced)
        
        if clean_reduced != clean_string(k):
             bridge_keys.add(reduced) # Store the "Human Readable" reduced version (still has parens maybe)
             
    print(f"Generated {len(bridge_keys)} bridge keys.")
    
    # Check for iPad Pro M4
    m4_bridges = [b for b in bridge_keys if "iPad Pro" in b and "M4" in b]
    print("\n--- iPad Pro M4 Bridges ---")
    for b in m4_bridges:
        print(b)
        
    # Check matching "iPad Pro M4 2024" against these
    input_str = "iPad Pro M4 2024"
    input_clean = clean_string(input_str)
    input_tokens = set(input_clean.split())
    
    print(f"\nScanning Input: '{input_str}' (Tokens: {input_tokens})")
    
    matches = []
    # Combine original and bridge
    all_models = keys + list(bridge_keys)
    all_models = sorted(all_models, key=len, reverse=True)
    
    for m in all_models:
        m_clean = clean_string(m)
        m_tokens = set(m_clean.split())
        if not m_tokens: continue
        if m_tokens.issubset(input_tokens):
            matches.append(m)
            
    print(f"Matches found: {matches[:5]}")

if __name__ == "__main__":
    main()
