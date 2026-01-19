import json
import glob
import pandas as pd
import re
import os
import numpy as np
import sqlite3
import statistics
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# --- CONFIGURATION ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

DB_FILE = os.path.join(SCRIPT_DIR, "apple_products_db.json")
CONTENT_DIR = os.path.join(PROJECT_ROOT, "content")
PRICES_DB = os.path.join(SCRIPT_DIR, "apple_prices.db")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "mappings_candidate.json")
SIMILARITY_THRESHOLD = 0.2

TARGET_DATE = "2026-01-18" # User requested specific date

# --- HELPER FUNCTIONS ---
def canonicalize_key(text):
    """Unify redundant terms into a single canonical target for the JSON output."""
    if not text: return ""
    text = text.replace('\u00a0', ' ')
    
    # 1. Unify Connectivity
    text = re.sub(r'\b(gps \+ cellular|gps \+ cellular|4g|5g|lte|cellular|sim)\b', 'Cellular', text, flags=re.IGNORECASE)
    
    # 2. Unify AirPods 4 ANC naming
    if "AirPods 4" in text and any(x in text.lower() for x in ["khử tiếng ồn", "chống ồn", "anc", "khử ồn"]):
        text = "AirPods 4 ANC"
    
    # 3. Clean up double spaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    # 4. Word deduplication
    words = text.split()
    seen = []
    for w in words:
        if not seen or w.lower() != seen[-1].lower():
            seen.append(w)
    return " ".join(seen)

def get_expanded_models(db_data):
    """Explodes base models into granular variants with full spec cross-products."""
    expanded = set()
    
    for model, info in db_data.items():
        expanded.add(canonicalize_key(model))
        
        family = info.get("Family", "")
        specs = info.get("Specs", {})
        
        # 1. IPHONE, MAC (Standard Storage Expansion)
        if family in ["iPhone", "Mac"] or "MacBook" in model:
            storage_text = ""
            for k, v in specs.items():
                if any(x in k for x in ["Dung Lượng", "Capacity", "Storage"]):
                    storage_text = " ".join(v)
                    break
            caps = re.findall(r'(\d+[GT]B)', storage_text)
            if not caps:
                if family == "Mac" or "MacBook" in model: caps = ["256GB", "512GB", "1TB"]
                else: caps = ["128GB", "256GB", "512GB"]
            
            for cap in set(caps):
                expanded.add(canonicalize_key(f"{model} {cap}"))
        
        # 2. WATCH (Size + Connectivity + Material)
        if family == "Watch" or "Watch" in model:
            sizes = set()
            for k, v in specs.items():
                text = " ".join(v).lower()
                found = re.findall(r'(\d{2})mm', text)
                sizes.update(found)
            
            materials = ["aluminum", "titanium"]
            material_text = ""
            for k, v in specs.items():
                 if "Chất Liệu" in k or "Material" in k:
                     material_text = " ".join(v).lower()
                     break
            if "titan" in material_text: materials = ["titanium"]
            elif "nhôm" in material_text: materials = ["aluminum"]
            
            fallback_sizes = ["40", "44"]
            if "Series 10" in model or "Series 11" in model: fallback_sizes = ["42", "46"]
            elif "Ultra" in model: fallback_sizes = ["49"]
            
            for size in (sizes if sizes else fallback_sizes):
                for mat in materials:
                    base_variant = f"{model} {size}mm {mat.capitalize()}"
                    expanded.add(canonicalize_key(f"{base_variant} GPS"))
                    expanded.add(canonicalize_key(f"{base_variant} Cellular"))

        # 3. IPAD (CROSS-PRODUCT: Size x Storage x Connectivity)
        if family == "iPad":
            s_found = re.search(r'(\d+[\.,]\d+|\d+)\s*(?:inch|”)', model)
            model_sizes = [s_found.group(1).replace(",", ".")] if s_found else []
            if not model_sizes:
                if "A16" in model: model_sizes = ["11"]
                elif "mini" in model: model_sizes = ["7.9" if "thế hệ" in model.lower() else "8.3"]
                elif "Pro" in model or "Air" in model: model_sizes = ["11", "13"]
                else: model_sizes = ["10.9"]

            model_storages = []
            for k, v in specs.items():
                if any(x in k for x in ["Dung Lượng", "Capacity", "Storage"]):
                    found_st = re.findall(r'(\d+(?:GB|TB))', " ".join(v), re.I)
                    model_storages.extend(found_st)
            if not model_storages: model_storages = ["128GB", "256GB", "512GB", "1TB"]

            for s in model_sizes:
                for st in model_storages:
                    # Clean the base for any pre-existing connectivity strings to avoid "Wi-Fi Wi-Fi"
                    clean_model = re.sub(r'\b(wi-fi \+ cellular|wi-fi|wifi \+ cellular|wifi)\b', '', model, flags=re.I).strip()
                    
                    # Avoid redundant size string if already in clean_model (e.g. "iPad Pro 11-inch")
                    size_s = f"{s} inch"
                    if size_s.lower() in clean_model.lower() or s in clean_model:
                        base = f"{clean_model} {st}"
                    else:
                        base = f"{clean_model} {size_s} {st}"
                        
                    expanded.add(canonicalize_key(f"{base} Wi-Fi"))
                    expanded.add(canonicalize_key(f"{base} Wi-Fi + Cellular"))

        # 4. AIRPODS
        if "AirPods 4" in model:
             expanded.add("AirPods 4")
             expanded.add("AirPods 4 ANC") # Lowercase 'anc' ensures clean_string match

    # Add iPhone Air specifically if missing
    if any("iPhone Air" in k for k in db_data):
         for s in ["128GB", "256GB", "512GB", "1TB"]:
             expanded.add(canonicalize_key(f"iPhone Air {s}"))

    return sorted(list(expanded), key=len, reverse=True)

# --- ALIAS & BLOCKING ---
ALIAS_MAP = {
    "ipad 9": "iPad (thế hệ thứ 9)",
    "ipad 10": "iPad (thế hệ thứ 10)",
    "ipad mini 6": "iPad mini (thế hệ thứ 6)",
    "ipad mini 7": "iPad mini (A17 Pro)",
    "ipad air 6": "iPad Air (M2)",
    "airpods pro 2": "AirPods Pro (thế hệ thứ 2) với Hộp sạc MagSafe (USB-C)",
    "titan": "titanium",
    "nhôm": "aluminum",
}

BLOCKING_TOKENS = {
    "ultra": ["ultra"], "pro": ["pro"], "max": ["max"], "plus": ["plus"], "mini": ["mini"],
    "air": ["air"], "cellular": ["cellular"], "anc": ["anc"], "titanium": ["titanium"],
    "iphone": ["iphone"], "ipad": ["ipad"], "watch": ["watch"], "macbook": ["macbook"],
    "128gb": ["128gb"], "256gb": ["256gb"], "512gb": ["512gb"], "1tb": ["1tb"], "2tb": ["2tb"],
    "size11": ["11 inch", "10.9 inch", "10.86 inch"],
    "size13": ["13 inch", "12.9 inch"],
    "v_m1": ["m1"], "v_m2": ["m2"], "v_m3": ["m3"], "v_m4": ["m4"], "v_m5": ["m5"],
    "v_a16": ["a16"], "v_a17": ["a17"], "v_a18": ["a18"]
}

def clean_string(text):
    if not isinstance(text, str): return ""
    text = text.lower().replace('\u00a0', ' ')
    # Standardize terms
    text = re.sub(r'\b(gps \+ cellular|4g|5g|lte|cellular|sim)\b', 'cellular', text)
    text = re.sub(r'\b(titan|ti)\b', 'titanium', text)
    text = re.sub(r'\b(nhôm|alum)\b', 'aluminum', text)
    text = re.sub(r'\b(chống ồn|khử tiếng ồn|anc)\b', 'anc', text)
    # Apply Aliases with word boundaries
    for k, v in ALIAS_MAP.items():
        text = re.sub(r'\b' + re.escape(k) + r'\b', v.lower(), text)
    # Standardize units
    text = re.sub(r'(\d+)\s*gb\b', r'\1gb', text)
    text = re.sub(r'(\d+)\s*tb\b', r'\1tb', text)
    text = re.sub(r'(\d+[\.,]\d+|\d+)\s*(?:inch|”|")\b', r'\1 inch', text)
    # Standardize versions
    text = re.sub(r'\b(m\d|a\d+)\b', r'\1', text)
    # Final cleanup
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

# --- DATA LOADING ---
def load_raw_data():
    # Use specific TARGET_DATE
    target_dir = os.path.join(CONTENT_DIR, TARGET_DATE)
    if not os.path.exists(target_dir):
        print(f"❌ Target directory not found: {target_dir}") 
        return pd.DataFrame()
        
    print(f"📂 Loading data from: {TARGET_DATE}")
    all_dfs = []
    for f in glob.glob(os.path.join(target_dir, "*.csv")):
        try:
            df = pd.read_csv(f, engine='python', sep=None, on_bad_lines='skip')
            df.columns = [c.lower().strip() for c in df.columns]
            rename_map = {'product_name': 'name', 'gia_khuyen_mai': 'price', 'gia_ban': 'price'}
            actual_rename = {k: v for k, v in rename_map.items() if k in df.columns}
            df.rename(columns=actual_rename, inplace=True)
            if 'name' in df.columns:
                df['name'] = df['name'].fillna('').astype(str) # Force String
                if 'price' not in df.columns: df['price'] = 0
                def cp(p):
                    if pd.isna(p) or isinstance(p, (int, float)): return float(p or 0)
                    s = str(p).replace('.', '').replace(',', '').replace('₫', '').strip()
                    try: return float(re.search(r'\d+', s).group())
                    except: return 0.0
                df['price'] = df['price'].apply(cp)
                all_dfs.append(df[['name', 'price']])
        except: continue
    return pd.concat(all_dfs, ignore_index=True).drop_duplicates('name') if all_dfs else pd.DataFrame()

def get_historical_median_prices():
    if not os.path.exists(PRICES_DB): return {}
    try:
        conn = sqlite3.connect(PRICES_DB)
        rows = conn.execute("SELECT m.normalized_key, p.price FROM prices p JOIN mappings m ON p.raw_name = m.raw_name WHERE p.price > 100000").fetchall()
        conn.close()
        data = {}
        for k, p in rows:
            if k not in data: data[k] = []
            data[k].append(p)
        return {k: statistics.median(v) for k, v in data.items()}
    except: return {}

# --- ML CORE ---
def train_and_predict(official_keys, raw_names, raw_prices):
    vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4))
    clean_official = [clean_string(k) for k in official_keys]
    clean_raw = [clean_string(r) for r in raw_names]
    official_constraints = [get_blocking_constraints(k) for k in clean_official]
    vectorizer.fit(clean_official + clean_raw)
    tfidf_official = vectorizer.transform(clean_official)
    tfidf_raw = vectorizer.transform(clean_raw)
    cosine_sim = cosine_similarity(tfidf_raw, tfidf_official)
    history_meds = get_historical_median_prices()
    
    mappings, review_needed = {}, []
    negative_tokens = ["bao chống sốc", "ốp lưng", "cường lực", "dây đeo"]
    
    for idx, raw in enumerate(raw_names):
        raw_clean = clean_raw[idx]
        raw_cons = get_blocking_constraints(raw_clean)
        scores = cosine_sim[idx]
        sorted_indices = np.argsort(scores)[::-1]
        
        best_match = None
        for cand_idx in sorted_indices[:15]:
            if scores[cand_idx] < SIMILARITY_THRESHOLD: break
            if raw_cons.issubset(official_constraints[cand_idx]):
                best_match = official_keys[cand_idx]
                break
        
        if best_match:
            # Filters
            is_acc = any(t in raw.lower() for t in negative_tokens)
            curr_p = raw_prices[idx]
            hist_med = history_meds.get(best_match)
            price_outlier = False
            if curr_p > 0 and hist_med:
                if curr_p < hist_med * 0.4 or curr_p > hist_med * 2.0: price_outlier = True
            
            if is_acc or price_outlier:
                review_needed.append(raw)
            else:
                if best_match not in mappings: mappings[best_match] = []
                mappings[best_match].append(raw)
        else:
            review_needed.append(raw)
    return mappings, review_needed

if __name__ == "__main__":
    with open(DB_FILE, 'r') as f: db_data = json.load(f)
    official_keys = get_expanded_models(db_data)
    raw_df = load_raw_data()
    if not raw_df.empty:
        maps, rev = train_and_predict(official_keys, raw_df['name'].tolist(), raw_df['price'].tolist())
        maps["_REVIEW_NEEDED_"] = sorted(rev)
        with open(OUTPUT_FILE, 'w') as f: json.dump(dict(sorted(maps.items())), f, ensure_ascii=False, indent=2)
        print(f"✅ Mapped {len(raw_df)-len(rev)} items. {len(rev)} need review.")
