
import re

# COPIED FROM normalize_ml.py

ALIAS_MAP = {
    "titan": "titanium",
    "series 10 titan": "Apple Watch Series 10 Titanium",
    "watch s10 titan": "Apple Watch Series 10 Titanium",
}

BLOCKING_TOKENS = {
    "ultra": ["ultra"],
    "pro": ["pro"], 
    "max": ["max"],
    "plus": ["plus"],
    "mini": ["mini"],
    "air": ["air"],
    "series": ["series", "s9", "s10", "s8"],
    "titanium": ["titanium"] 
}

def clean_string(text):
    if not isinstance(text, str): return ""
    text = text.lower()
    
    # 1. Apply Aliases First (Use Regex for Safety)
    # Sort aliases by length descending to match longest first
    sorted_aliases = sorted(ALIAS_MAP.keys(), key=len, reverse=True)
    
    for alias in sorted_aliases:
        if alias in text:
             # Prevent replacing "titan" inside "titanium"
             pattern = r'(?<!\w)' + re.escape(alias) + r'(?!\w)'
             text = re.sub(pattern, ALIAS_MAP[alias], text)
    
    # 2. Basic cleaning
    text = re.sub(r'[^\w\s]', ' ', text) # Remove punctuation
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def get_blocking_constraints(text):
    constraints = set()
    tokens = set(text.split())
    for key, variants in BLOCKING_TOKENS.items():
        for v in variants:
            if v in tokens:
                constraints.add(key)
                break
    return constraints

# TEST CASE
raw_input = "iPad Mini 7 8.3 inch 5G (128GB)"
cand_bad = "iPad mini (thế hệ thứ 6)" # Or iPad mini 3 (Wait, 3 isn't blocking, so might match)
cand_good = "iPad mini (A17 Pro) Wi-Fi"

print(f"--- INPUT: {raw_input} ---")
clean_in = clean_string(raw_input)
print(f"Clean Input: '{clean_in}'")
cons_in = get_blocking_constraints(clean_in)
print(f"Constraints Input: {cons_in}")

print(f"\n--- CANDIDATE GOOD: {cand_good} ---")
clean_good = clean_string(cand_good)
print(f"Clean Good: '{clean_good}'")
cons_good = get_blocking_constraints(clean_good)
print(f"Constraints Good: {cons_good}")
print(f"Subset Check (Input <= Good)? {cons_in.issubset(cons_good)}")
