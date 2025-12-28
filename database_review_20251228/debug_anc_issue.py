
import re
import json

# Replicate Logic
ALIAS_MAP = {
    "airpods 4 chong on": "AirPods 4 với tính năng Khử tiếng ồn chủ động",
    "airpods 4 chống ồn": "AirPods 4 với tính năng Khử tiếng ồn chủ động",
}

BLOCKING_TOKENS = {
    "anc": ["khử tiếng ồn", "chống ồn", "anc"]
}

def clean_string(text):
    if not isinstance(text, str): return ""
    text = text.lower()
    text = text.replace('\u00a0', ' ')
    
    # 2. Apply Aliases
    sorted_aliases = sorted(ALIAS_MAP.keys(), key=len, reverse=True)
    for alias in sorted_aliases:
        if alias in text:
             pattern = r'(?<!\w)' + re.escape(alias) + r'(?!\w)'
             text = re.sub(pattern, ALIAS_MAP[alias], text)
    
    text = re.sub(r'[^\w\s]', ' ', text) 
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def get_blocking_constraints(text):
    constraints = set()
    for key, variants in BLOCKING_TOKENS.items():
        for v in variants:
            pattern = r'\b' + re.escape(v) + r'\b'
            if re.search(pattern, text):
                constraints.add(key)
                break
    return constraints

# TEST
raw = "AirPods 4 (chống ồn)"
cand_anc = "AirPods 4 với tính năng Khử tiếng ồn chủ động"
cand_base = "AirPods 4"

print(f"RAW: {raw}")
clean_raw = clean_string(raw)
cons_raw = get_blocking_constraints(clean_raw)
print(f"  Clean: '{clean_raw}'")
print(f"  Cons: {cons_raw}")

print(f"\nCAND ANC: {cand_anc}")
clean_anc = clean_string(cand_anc)
cons_anc = get_blocking_constraints(clean_anc)
print(f"  Clean: '{clean_anc}'")
print(f"  Cons: {cons_anc}")

print(f"\nCAND BASE: {cand_base}")
clean_base = clean_string(cand_base)
cons_base = get_blocking_constraints(clean_base)
print(f"  Clean: '{clean_base}'")
print(f"  Cons: {cons_base}")

print(f"\nSubset check (Raw in ANC): {cons_raw.issubset(cons_anc)}")
print(f"Subset check (Raw in Base): {cons_raw.issubset(cons_base)}")
