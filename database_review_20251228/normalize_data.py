import glob
import csv
import json
import os
import re
from collections import defaultdict

# Configuration
# --- CONFIGURATION ---
CONTENT_DIR = "content"
OUTPUT_FILE = "mappings_candidate.json"
APPLE_DB_FILE = "apple_products_db.json"

JUNK_PREFIXES = [
    "Khuyến mãi", "Trả góp", "Tặng", "Giảm", "Thu cũ", "Ưu đãi", 
    "Mua kèm", "Nhập mã", "Thanh toán", "Phiếu mua hàng", "Chương trình", 
    "Error", "429 Too Many Requests",
    # Accessories
    "Bao da", "Bao chống sốc", "Ốp lưng", "Cường lực", "Dây đeo", "Miếng dán",
    "Sạc dự phòng", "Cáp sạc", "Củ sạc", "Adapter", "Tai nghe", "Chuột", "Bàn phím"
]

# Aliases for colloquial names to Official DB Keys (partial or full)
ALIAS_MAP = {
    "ipad mini 7": "iPad mini (A17 Pro)",
    "ipad mini 2024": "iPad mini (A17 Pro)",
    "imac m4": "iMac (24 inch, 2024, Bốn cổng)",
    "ipad 10": "iPad (thế hệ thứ 10)",
    "ipad gen 10": "iPad (thế hệ thứ 10)",
    "ipad 9": "iPad (thế hệ thứ 9)",
    "ipad gen 9": "iPad (thế hệ thứ 9)",
    # AirPods Aliases
    "airpods 2": "AirPods (thế hệ thứ 2)",
    "airpods 3": "AirPods (Thế hệ thứ 3)",
    "airpods pro 2": "AirPods Pro (thế hệ thứ 2) với Hộp sạc MagSafe (USB-C)", # Most common current model
    "airpods pro gen 2": "AirPods Pro (thế hệ thứ 2) với Hộp sạc MagSafe (USB-C)",
    "airpods pro 3": "AirPods Pro 3", # Explicitly map Pro 3
    "airpods pro": "AirPods Pro (thế hệ thứ 1) with Wireless Charging Case", # Old model fallback
    "airpods max": "AirPods Max", # Check if DB has "AirPods Max" or "AirPods Max với cổng USB-C"
    "airpods 4": "AirPods 4", # Short key is fine if DB has it
    "airpods 4 anc": "AirPods 4 với tính năng Khử tiếng ồn chủ động",
    # Apple Watch
    "titan": "titanium",
    "series 10 titan": "Apple Watch Series 10 Titanium",
    "series 10 titanium": "Apple Watch Series 10 Titanium",
    "watch s10 titan": "Apple Watch Series 10 Titanium"
}

# --- SMART DICTIONARY ---
# Load Official Apple Models from DB
KNOWN_MODELS = []
try:
    if os.path.exists(APPLE_DB_FILE):
        with open(APPLE_DB_FILE, 'r', encoding='utf-8') as f:
            db_data = json.load(f)
            # Sort by length descending to match longest specific name first (e.g. "MacBook Pro 16" before "MacBook Pro")
            KNOWN_MODELS = sorted(list(db_data.keys()), key=len, reverse=True)
            print(f"✅ Loaded {len(KNOWN_MODELS)} models from {APPLE_DB_FILE}")
    else:
        print(f"⚠️  {APPLE_DB_FILE} not found. Using fallback dictionary.")
        raise FileNotFoundError
except Exception as e:
    # Fallback Hardcoded Dictionary
    KNOWN_MODELS = [
        "iPhone 16 Pro Max", "iPhone 16 Pro", "iPhone 16 Plus", "iPhone 16",
        "iPhone 15 Pro Max", "iPhone 15 Pro", "iPhone 15 Plus", "iPhone 15",
        "iPhone 14 Pro Max", "iPhone 14 Pro", "iPhone 14 Plus", "iPhone 14",
        "iPhone 13 Pro Max", "iPhone 13 Pro", "iPhone 13 mini", "iPhone 13",
        "iPhone 12 Pro Max", "iPhone 12 Pro", "iPhone 12 mini", "iPhone 12",
        "iPhone 11 Pro Max", "iPhone 11 Pro", "iPhone 11",
        "MacBook Air M3", "MacBook Air M2", "MacBook Air M1",
        "MacBook Pro M3", "MacBook Pro M2", "MacBook Pro M1",
        "MacBook Pro 14", "MacBook Pro 16",
        "iPad Pro M4", "iPad Pro 12.9", "iPad Pro 11",
        "iPad Air M2", "iPad Air 5", "iPad Air 4",
        "iPad mini 6", "iPad Gen 10", "iPad Gen 9",
        "Apple Watch Ultra 2", "Apple Watch Ultra",
        "Apple Watch Series 9", "Apple Watch Series 8", "Apple Watch SE",
        "AirPods Pro 2", "AirPods 3", "AirPods 2", "AirPods Max",
        "Mac mini M2", "Mac Studio M2", "Mac Pro"
    ]
    # Ensure sorted by length
    KNOWN_MODELS = sorted(KNOWN_MODELS, key=len, reverse=True)

def is_junk(name):
    if not name or len(name) < 3: return True
    norm = name.strip()
    # Check prefixes
    for prefix in JUNK_PREFIXES:
        if norm.lower().startswith(prefix.lower()):
            return True
    return False

def clean_string(text):
    """Aggressively strip common filler words to reveal the Core Name."""
    text = text.lower()
    
    # Removals - Add "inch", "gen", "wifi", "cellular" to unify variants
    for w in ["tai nghe", "bluetooth", "chính hãng", "vn/a", "apple", "bản", "hộp", "sạc", "mới", "cũ", 
              "điện thoại", "máy tính bảng", "laptop", "đồng hồ", "thông minh", "bao da", "ốp lưng",
              "thế hệ", "thứ", # Vietnamese fillers
              "thế hệ", "thứ", # Vietnamese fillers
              "generation", "gen", "(", ")", ",", "-"]:
        text = text.replace(w, " ")
        
    # Ordinals: 9th -> 9, 1st -> 1
    text = re.sub(r'(\d+)(st|nd|rd|th)\b', r'\1', text)
        
    # Remove chars
    text = re.sub(r'[^\w\s]', ' ', text)
    return " ".join(text.split())

def generate_bridge_keys(known_models):
    """
    Generate simplified keys (Bride Keys) from official matched models.
    Goal: Allow ambiguous inputs (e.g. "iPad Pro M4") to match specific DB keys (e.g. "iPad Pro 11-inch (M4)").
    Strategy: 
    1. Strip Size (e.g. "11-inch", "13-inch")
    2. Strip Connectivity (e.g. "Wi-Fi + Cellular")
    3. Create a map: Simplified Token Set -> Original Model Name
    """
    bridge_map = {}
    
    for model in known_models:
        # Regex to remove size patterns
        # Pattern: (11|13|14|15|16|24|27)(-|\s)?inch
        # Also remove decimal sizes like 10.9-inch or 12.9-inch
        # Also Vietnamese "inch" might be consistent or scraped as is
        reduced = re.sub(r'\b(1[0-9]|2[0-9])(\.\d+)?(-|\s)?inch\b', '', model, flags=re.IGNORECASE)
        
        # Remove Connectivity common terms from Key (Wi-Fi, Cellular) to match base
        # But wait, we want "iPad Pro M4" to match.
        # "iPad Pro 11-inch (M4) Wi-Fi" -> "iPad Pro (M4)"
        # "iPad Pro 11-inch (M4) Wi-Fi + Cellular" -> "iPad Pro (M4)"
        
        # Remove "Wi-Fi" and "Cellular"
        reduced = reduced.replace("Wi-Fi", "").replace("Cellular", "").replace("+", "")
        
        # Clean up
        reduced_clean = clean_string(reduced)
        reduced_tokens = frozenset(reduced_clean.split())
        
        # Map tokens to valid model. 
        # CAUTION: Multiple models might map to same bridge (11 vs 13 inch).
        # We prefer the 11-inch usually? Or just pick the first one (alphabetical or length).
        # OR we map to the *Shortest* official key? No.
        # We just pick one. Ideally user input usually implies base model if unspecified.
        # Let's map to the first one seen (since known_models is sorted by length DESC, first one is longest).
        # Actually we might want the shortest "Base" model? 
        # Let's just store all candidates and pick best?
        # For now, just First.
        
        if reduced_tokens and reduced_tokens not in bridge_map:
            bridge_map[reduced_tokens] = model
            
    return bridge_map

# Load Official & Generate Bridges
# We want to merge the Bridge Keys into the main search list so they are prioritized by length/specificity.
# e.g. "iPad Pro (M4)" (longer) should match before "iPad Pro" (shorter).

MATCHING_KEYS = [] # Will hold KNOWN_MODELS + BRIDGE_KEYS

def match_known_model(raw_name):
    """Find the best matching known model using TOKEN SUBSET matching."""
    global MATCHING_KEYS
    
    # Pre-process Aliases
    clean_name = clean_string(raw_name).lower()
    for alias, replacement in ALIAS_MAP.items():
        if alias in clean_name:
            # Replace alias in the input string to help matching
            # e.g. "ipad mini 7 64gb" -> "ipad mini (a17 pro) 64gb"
            # This helps the token matcher find the official key "iPad mini (A17 Pro)..."
            raw_name = raw_name.lower().replace(alias, replacement)
            clean_name = clean_string(raw_name) # Re-clean
            break

    # Lazy Initialization of Unified Key List
    if not MATCHING_KEYS and KNOWN_MODELS:
        print("⚡️ Generating Bridge Keys & Unifying Search Space...")
        bridge_map = generate_bridge_keys(KNOWN_MODELS)
        
        # We need a way to return the *Original* key if we matched a Bridge Key.
        # But we also want the Bridge Key to act as the "Model Name" for grouping if it's better?
        # Actually, if we map "iPad Pro M4" -> "iPad Pro 11-inch (M4)...", that's specific.
        # But if we don't know the inch, we CAN'T map to the specific 11-inch key safely.
        # We should map to the **Bridge Key** itself (e.g. "iPad Pro (M4)") as the canonical name for these rows.
         
        # So we simply add bridge keys to the list.
        # But wait, `KNOWN_MODELS` logic returns `model`. 
        # If we iterate a combined list, we return the match.
        
        unique_keys = set(KNOWN_MODELS) # Start with officials
        
        # Add bridges
        for bridge_tokens, original in bridge_map.items():
            # bridge_tokens is a strict set. We need the string representation for the key?
            # No, our loop takes a string key, cleans it, tokens it.
            # We construct a string "Fake" key from the tokens? no.
            # We generated bridge strings in `generate_bridge_keys` but discarded them?
            # Wait, `generate_bridge_keys` returns map[frozenset -> original].
            # That's hard to integrate into the string-loop.
            pass

        # Let's Refactor:
        # We need a list of (KeyString, ReturnValue).
        # For Official: Key="iPad Pro 11..", Return="iPad Pro 11.."
        # For Bridge: Key="iPad Pro (M4)", Return="iPad Pro (M4)" <--- This allows grouping by the generic-but-specific-chip name.
        
        # Only issue: `generate_bridge_keys` calculated tokens directly.
        # Let's reimplement `generate_bridge_keys` to strictly return a dict of { "Bridge Name String": "Original (unused?)" }
        # Actually we just want the Bridge Name String to be added to keys.
        
        # Let's adjust `generate_bridge_keys` in the code block below first.
        pass

    # ... logic continues ...
    
    # 1. Clean and Tokenize Input
    input_clean = clean_string(raw_name)
    input_tokens = set(input_clean.split())
    
    # 2. Special Fixes
    if "chống ồn" in input_clean or "anc" in input_clean:
         if "airpods 4" in input_clean: return "AirPods 4 ANC"
            
    # Priority Search: Check Bridge Keys AND Official Keys together.
    # To do this, we need a refined generation step. See `prepare_matching_keys` helper.
    if not MATCHING_KEYS:
        MATCHING_KEYS = prepare_matching_keys(KNOWN_MODELS)
        
    for key in MATCHING_KEYS:
        key_clean = clean_string(key)
        key_tokens = set(key_clean.split())
        if not key_tokens: continue
        
        if key_tokens.issubset(input_tokens):
            return key
            
    return None

def prepare_matching_keys(officials):
    """
    Creates a master list of keys: Official + Bridge.
    Sorted by Length Descending (Specificity).
    """
    uniques = set(officials)
    
    # Generate Bridges Strings
    for model in officials:
        # Strip Size & Connectivity
        # Handle dot or comma decimal: 12.9 or 12,9
        reduced = re.sub(r'\b(1[0-9]|2[0-9])([.,]\d+)?(-|\s)?inch\b', '', model, flags=re.IGNORECASE)
        reduced = reduced.replace("Wi-Fi", "").replace("Cellular", "").replace("+", "").replace("GPS", "")
        # Also strip Year (e.g. 2021, 2024) to allow "MacBook Air M4" to match "MacBook Air (M4, 2024)"
        reduced = re.sub(r'\b202[0-9]\b', '', reduced)
        
        # Cleanup Punctuation artifacts from removals
        # Remove empty parens: () or ( )
        reduced = re.sub(r'\(\s*\)', '', reduced)
        # Remove leading comma inside parens: (, result -> (result
        reduced = re.sub(r'\(\s*,', '(', reduced)
        # Remove trailing comma inside parens: result, ) -> result)
        reduced = re.sub(r',\s*\)', ')', reduced)
        # Remove double commas
        reduced = re.sub(r',\s*,', ',', reduced)
        # Remove leading/trailing commas matches generally if they appear (less likely but possible)
        
        reduced = " ".join(reduced.split()) # condense spaces
        
        # Final cleanup: Remove space inside parens "( M4)" -> "(M4)"
        reduced = re.sub(r'\(\s+', '(', reduced)
        
        # Add parentheses if stripped info left bare "iPad Pro M4"? 
        # Actually generic keys like "iPad Pro (M4)" are good.
        # "iPad Pro 11-inch (M4)" -> "iPad Pro (M4)"
        # "iPad Air 13-inch (M2)" -> "iPad Air (M2)"
        
        if len(reduced) > 3 and reduced != model:
             uniques.add(reduced)
             
    return sorted(list(uniques), key=len, reverse=True)

def extract_variants(text):
    """Use Regex to extract specs (RAM, Storage, Chip)."""
    text = text.upper() # Standardize to upper for regex
    specs = []
    
    # 1. RAM (e.g. 8GB, 16GB, 32GB)
    # Avoid matching "128GB" which is usually storage. 
    # Heuristic: RAM is usually < 128GB, Storage >= 128GB (except older phones)
    # But usually mapped as X/Y e.g. 8GB/256GB.
    
    # Extract all GB/TB patterns
    # Pattern: number followed optionally by space, then GB or TB
    patterns = re.findall(r'(\d+)\s*(GB|TB)', text)
    
    ram = None
    storage = None
    
    for val_str, unit in patterns:
        val = int(val_str)
        if unit == 'TB':
            storage = f"{val}TB"
        elif unit == 'GB':
            if val < 64: # Assume < 64GB is RAM (Mac/PC logic) - Phones might differ (iPhone 13 can have 4GB RAM hidden but 128GB storage)
                if not ram: ram = f"{val}GB"
            else:
                if not storage: storage = f"{val}GB"
    
    if ram: specs.append(ram)
    if storage: specs.append(storage)
        
    # 2. Chip (M1, M2...)
    # Already captured? Maybe.
    
    # 3. Case Size (e.g. 40mm, 44mm, 46mm)
    # Important for Watches
    size = re.search(r'(\d+)mm', text, re.IGNORECASE)
    if size:
        specs.append(f"{size.group(1)}mm")

    # 4. Chip Detailed
    cpu_gpu = re.search(r'(\d+)CPU\s*(\d+)GPU', text)
    if cpu_gpu:
        specs.append(f"{cpu_gpu.group(1)}c/{cpu_gpu.group(2)}c")

    # 5. Screen Size (inch) - For iPads/Macs differentiation
    inch_size = re.search(r'\b(\d+(?:[.,]\d+)?)\s*inch', text, re.IGNORECASE)
    if inch_size:
        specs.append(f"{inch_size.group(1)} inch")

    # 6. Connectivity (Wifi/5G)
    if re.search(r'\b(5G|LTE|4G|Cellular)\b', text, re.IGNORECASE):
        specs.append("5G")
    elif re.search(r'\b(Wifi)\b', text, re.IGNORECASE):
        specs.append("Wifi")

    # 7. Texture (Nano/Standard)
    if re.search(r'Nano(-texture)?', text, re.IGNORECASE):
        specs.append("Nano-texture")
    elif re.search(r'Standard( Glass)?', text, re.IGNORECASE):
        # Only explicitly add Standard if user specified, to differentiate from Nano
        specs.append("Standard Glass")
        
    return "/".join(specs) if specs else None

def main():
    print(f"🔍 Scanning CSVs in {CONTENT_DIR}...")
    files = glob.glob(os.path.join(CONTENT_DIR, "**", "*.csv"), recursive=True)
    
    raw_names = set()
    for f in files:
        try:
            with open(f, 'r', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile, delimiter=';')
                header = next(reader, None)
                if not header: continue
                try:
                    name_idx = header.index("Product_Name")
                except: continue
                for row in reader:
                    if len(row) > name_idx:
                        name = row[name_idx].strip()
                        if not is_junk(name):
                            raw_names.add(name)
        except: pass
            
    print(f"✨ Processing {len(raw_names)} unique names...")
    
    mappings = defaultdict(list)
    unknowns = []
    
    for name in raw_names:
        model = match_known_model(name)
        if model:
            # ProDB Logic: Extract Variants
            specs_str = extract_variants(name)
            if specs_str:
                specs_list = specs_str.split("/")
                filtered_specs = []
                # Deduplicate: Don't add variant if already in Model Name
                # Clean model name for check
                m_lower = model.lower().replace("-", "").replace(" ", "")
                for s in specs_list:
                    s_lower = s.lower().replace("-", "").replace(" ", "")
                    # Alias Checks
                    if "5g" in s_lower and "cellular" in m_lower: continue
                    if "wifi" in s_lower and "wifi" in m_lower: continue
                    if "standard" in s_lower and "standard" not in m_lower: 
                        filtered_specs.append(s)
                        continue
                        
                    if s_lower in m_lower: continue
                    filtered_specs.append(s)
            
            # FORCE BASE MODEL MAPPING
            # We ignore filtered_specs for the Key to ensure FK consistency with `products` table.
            full_key = model
                
            mappings[full_key].append(name)
        else:
            unknowns.append(name)
            
    # Add Unknowns to mapping under "Review Needed"
    mappings["_REVIEW_NEEDED_"] = sorted(unknowns)
    
    # Sort
    sorted_map = dict(sorted(mappings.items()))
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(sorted_map, f, indent=2, ensure_ascii=False)
        
    print(f"✅ Auto-Mapped {len(raw_names) - len(unknowns)} items.")
    print(f"⚠️  Review Needed for {len(unknowns)} items.")
    print(f"📂 Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
