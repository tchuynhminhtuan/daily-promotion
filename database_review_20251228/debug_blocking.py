
import json
import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# --- COPY FROM normalize_ml.py ---
ALIAS_MAP = {
    "ipad 9": "iPad (thế hệ thứ 9)",
    "ipad gen 9": "iPad (thế hệ thứ 9)",
    "ipad 10": "iPad (thế hệ thứ 10)",
    "ipad gen 10": "iPad (thế hệ thứ 10)",
    "ipad mini 6": "iPad mini (thế hệ thứ 6)",
    "ipad mini 7": "iPad mini (A17 Pro)",
    "ipad air 5": "iPad Air (thế hệ thứ 5)",
    "ipad air 6": "iPad Air (thế hệ thứ 6)",
    "airpods 2": "AirPods (thế hệ thứ 2)",
    "airpods 3": "AirPods (Thế hệ thứ 3)",
    "airpods pro 2": "AirPods Pro (thế hệ thứ 2) với Hộp sạc MagSafe (USB-C)", 
    "airpods pro gen 2": "AirPods Pro (thế hệ thứ 2) với Hộp sạc MagSafe (USB-C)",
    "airpods pro 3": "AirPods Pro 3", 
    "airpods pro": "AirPods Pro (thế hệ thứ 1) with Wireless Charging Case",
    "airpods max": "AirPods Max", 
    "airpods 4": "AirPods 4", 
    "airpods 4 anc": "AirPods 4 với tính năng Khử tiếng ồn chủ động",
    "airpods 4 chong on": "AirPods 4 với tính năng Khử tiếng ồn chủ động",
    "airpods 4 chống ồn": "AirPods 4 với tính năng Khử tiếng ồn chủ động",
    "titan": "titanium",
    "nhôm": "aluminum",
}

BLOCKING_TOKENS = {
    "ultra": ["ultra"], "pro": ["pro"], "max": ["max"], "plus": ["plus"], "mini": ["mini"], "air": ["air"],
    "series": ["series", "s9", "s10", "s8", "s11"], 
    "s1": ["s1", "series 1"], "s10": ["s10", "series 10"], "s11": ["s11", "series 11"],
    "se2": ["se 2", "se gen 2", "se 2024", "se 2023"],
    "se3": ["se 3", "se gen 3", "se 2025"],
    "titanium": ["titanium"], "aluminum": ["aluminum"], "cellular": ["cellular"],
    "anc": ["khử tiếng ồn", "chống ồn", "anc"],
    "iphone": ["iphone"], "ipad": ["ipad"], "macbook": ["macbook"], "imac": ["imac"],
    "watch": ["apple watch", "watch"],
    "mac_mini": ["mac mini", "mini m"], "mac_studio": ["mac studio"],
    "v_a14": ["a14"], "v_a15": ["a15"], "v_a16": ["a16"], "v_a17": ["a17"], "v_a18": ["a18"],
    "v_m1": ["m1"], "v_m2": ["m2"], "v_m3": ["m3"], "v_m4": ["m4"], "v_m5": ["m5"],
    "16gb": ["16gb", "16 gb"], "24gb": ["24gb", "24 gb"], "32gb": ["32gb", "32 gb"], "48gb": ["48gb", "48 gb"],
    "256gb": ["256gb", "256 gb"], "512gb": ["512gb", "512 gb"], "1tb": ["1tb", "1 tb"],
    "size11": ["11 inch", "11.1", "10.86"], "size13": ["13 inch", "13.6", "12.9"],
    "size14": ["14 inch", "14.2"], "size15": ["15 inch", "15.3"], "size16": ["16 inch", "16.2"]
}

def clean_string(text):
    if not isinstance(text, str): return ""
    text = text.lower().replace('\u00a0', ' ')
    text = re.sub(r'\b(4g|5g|lte|cellular|sim)\b', 'cellular', text)
    text = re.sub(r'\b(titan|titanium|ti)\b', 'titanium', text)
    text = re.sub(r'\b(nhôm|aluminum|alum)\b', 'aluminum', text)
    for alias in sorted(ALIAS_MAP.keys(), key=len, reverse=True):
        if alias in text:
            text = re.sub(r'(?<!\w)' + re.escape(alias) + r'(?!\w)', ALIAS_MAP[alias], text)
    text = re.sub(r'\b(chong on|chống ồn|anc|khu tieng on|khử tiếng ồn)\b', 'anc', text)
    text = re.sub(r'(\d+)\s*gb\b', r'\1gb', text)
    text = re.sub(r'(\d+)\s*tb\b', r'\1tb', text)
    text = re.sub(r'(\d+)\s*inch\b', r'\1 inch', text)
    text = re.sub(r'\bseries 10\b', 's10', text)
    text = re.sub(r'[^\w\s]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()

def get_blocking_constraints(text):
    constraints = set()
    for key, variants in BLOCKING_TOKENS.items():
        for v in variants:
            if re.search(r'\b' + re.escape(v) + r'\b', text):
                constraints.add(key)
                break
    return constraints

# --- DEBUG TEST ---
tests = [
    ("Apple Watch Series 10 42mm (GPS) Viền Nhôm - Dây Vải", "Apple Watch Series 10 42mm Aluminum GPS"),
    ("Apple Watch Series 11 42mm (5G) Viền Nhôm Dây Cao Su Size M/L", "Apple Watch Series 11 42mm Aluminum Cellular"),
    ("Mac Mini M4 2024 10CPU 10GPU 16GB/256GB", "Mac mini (2024) M4 16GB 256GB"),
    ("Laptop MacBook Air 13 inch M2 16GB/256GB", "MacBook Air (13-inch, M2, 2022) M2 16GB 256GB")
]

vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4))

for raw_name, cand_key in tests:
    clean_raw = clean_string(raw_name)
    clean_cand = clean_string(cand_key)
    cons_raw = get_blocking_constraints(clean_raw)
    cons_cand = get_blocking_constraints(clean_cand)
    
    vectorizer.fit([clean_raw, clean_cand])
    v1 = vectorizer.transform([clean_raw])
    v2 = vectorizer.transform([clean_cand])
    score = cosine_similarity(v1, v2)[0,0]

    print(f"\nRaw: '{raw_name}'\nCand: '{cand_key}'")
    print(f"  Clean Raw: '{clean_raw}'")
    print(f"  Clean Cand: '{clean_cand}'")
    print(f"  Cons Raw: {cons_raw}")
    print(f"  Cons Cand: {cons_cand}")
    print(f"  Subset: {cons_raw.issubset(cons_cand)}")
    if not cons_raw.issubset(cons_cand):
        print(f"  Missing: {cons_raw - cons_cand}")
    print(f"  Score: {score:.4f}")
