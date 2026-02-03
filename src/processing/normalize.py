
import pandas as pd
import yaml
import glob
import re
import os
import datetime
from datetime import timedelta
from pathlib import Path
from scipy import stats
import numpy as np

# Config
# Dynamic BASE_DIR: Works on both local and CI environments
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # src/processing/normalize.py -> daily-promotion/
CATALOG_PATH = BASE_DIR / "catalog/product_catalog.yaml"
COLOR_ALIASES_PATH = BASE_DIR / "catalog/color_aliases.yaml"
CONTENT_BASE = BASE_DIR / "data/raw"  # Base directory, will scan for dates
OUTPUT_DIR = BASE_DIR / "catalog/output"
LOGS_DIR = BASE_DIR / "data/logs"
INSIGHTS_DIR = BASE_DIR / "docs/insights"
CONTENT_DIR = CONTENT_BASE # Default content directory


RETAILER_MAP = {
    '1-fpt': 'FPT Shop',
    '2-mw': 'Mobile World', 
    '3-viettel': 'Viettel Store',
    '4-hoangha': 'HoangHa',
    '5-ddv': 'Di Động Việt',
    '6-cps': 'CellphoneS'
}

def load_catalog():
    with open(CATALOG_PATH, 'r') as f:
        return yaml.safe_load(f)

def load_color_aliases():
    if not os.path.exists(COLOR_ALIASES_PATH):
        return {}
    with open(COLOR_ALIASES_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def clean_price(price):
    val = None
    if pd.isna(price): return None
    
    if isinstance(price, (int, float)):
        val = float(price)
    else:
        s = str(price)
        # Let's clean standard delimiters first
        s_clean = re.sub(r'[.,]', '', s) 
        
        # Find all groups of digits
        matches = re.findall(r'\d+', s_clean)
        if not matches: return None
        
        # Take the first one? Or reasonable one?
        for m in matches:
            v = float(m)
            if v > 100000 and v < 200000000: 
                 val = v
                 break
    
    if val and 100000 < val < 200000000:
        return val
        
    return None

def normalize_text(text):
    # Remove non-breaking spaces and normalize white space
    text = str(text).lower()
    # Replace punctuation with space
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def normalize_storage(name):
    name = name.lower()
    # Find all matches: (number, unit)
    matches = re.findall(r'(\d+)\s*(gb|tb)', name)
    
    if not matches:
        return "unknown_storage"
        
    candidates = []
    for val_str, unit in matches:
        val = int(val_str)
        # Convert to GB for comparison
        size_gb = val * 1024 if unit == 'tb' else val
        
        # Filter out common RAM-only sizes (unlikely to be storage for this catalog)
        # 8, 12, 18, 24, 36, 40, 48, 96 GB are typically RAM in modern Apple Silicon era.
        # 16, 32, 64, 128... can be both.
        # But if we have multiple candidates, we usually want the LARGEST as storage.
        # Example: "8GB 256GB" -> 256 is storage.
        # Example: "18GB 512GB" -> 512 is storage.
        if size_gb in [4, 6, 8, 12, 18, 24, 36, 40, 48, 96]:
            continue
            
        candidates.append((size_gb, val, unit))
        
    if not candidates:
        return "unknown_storage"
        
    # Sort by size descending
    candidates.sort(key=lambda x: x[0], reverse=True)
    
    # Return largest
    best_val, best_unit = candidates[0][1], candidates[0][2]
    return f"{best_val}{best_unit.upper()}"

# New Config
MAPPING_PATH = BASE_DIR / "catalog/retailer_mapping.yaml"

def load_retailer_mapping():
    if not os.path.exists(MAPPING_PATH): return {}
    with open(MAPPING_PATH, 'r') as f:
        return yaml.safe_load(f)

# AI Configuration
AI_MODEL_PATH = BASE_DIR / "experiments/fine_tuning/adapters"
BASE_MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
_AI_MODEL = None
_AI_TOKENIZER = None
_AI_CACHE = {} # Cache for AI predictions to improve speed
AI_ENABLED = True  # Global flag to enable/disable AI (set via --no-ai)

def load_ai_model():
    global _AI_MODEL, _AI_TOKENIZER
    if _AI_MODEL is None:
        try:
            from mlx_lm import load
            print(f"🤖 Loading AI Model from {AI_MODEL_PATH}...")
            _AI_MODEL, _AI_TOKENIZER = load(BASE_MODEL_ID, adapter_path=str(AI_MODEL_PATH))
        except Exception as e:
            # print(f"⚠️ Failed to load AI model: {e}")
            return False
    return True

def ai_predict_key(product_name):
    global _AI_MODEL, _AI_TOKENIZER
    if not _AI_MODEL: return None
    
    try:
        from mlx_lm import generate
        SYSTEM_PROMPT = "You are a product matching assistant. Map the retailer product name to the correct canonical key."
        prompt = f"<|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>\n<|im_start|>user\nMap this product: {product_name}<|im_end|>\n<|im_start|>assistant\n"
        
        response = generate(_AI_MODEL, _AI_TOKENIZER, prompt=prompt, max_tokens=20, verbose=False)
        pred_key = response.strip()

        # Hybrid Rules (Same as Benchmark)
        p_lower = product_name.lower()
        if "gps" in p_lower and "lte" not in p_lower and "cellular" not in p_lower:
            pred_key = pred_key.replace("_lte", "_gps").replace("_cellular", "_gps").replace("_gps_gps", "_gps")
        if "wifi" in p_lower and "5g" not in p_lower:
             pred_key = pred_key.replace("_5g", "").replace("_lte", "").replace("_cellular", "")
        
        return pred_key
    except:
        return None

def match_product(row_name, row_specs, catalog, retailer_name=None, retailer_mapping=None):
    # 1. Exact Match via Retailer Mapping (Priority)
    if retailer_name and retailer_mapping and retailer_name in retailer_mapping:
         mapped_key = retailer_mapping[retailer_name].get(str(row_name).strip())
         if mapped_key:
             return mapped_key

    # 2. AI Fallback (New V3 Layer)
    # Skip if AI is disabled (e.g., --no-ai flag for CI/CD)
    if not AI_ENABLED:
        pass  # Skip to legacy fallback
    else:
        # OPTIMIZATION: Only call AI for reasonable product names to avoid spam latency
        spam_keywords = ["giảm", "ưu đãi", "thanh toán", "thẻ tín dụng", "vnpay", "hoàn tiền", "chính sách", "liên hệ", "trả góp", "quà tặng", "v ch"]
        name_lower = str(row_name).lower()
        
        # Check Cache First
        global _AI_CACHE
        if row_name in _AI_CACHE:
            return _AI_CACHE[row_name]


            
        if len(row_name) < 100 and not any(k in name_lower for k in spam_keywords):
            if load_ai_model():
                pred = ai_predict_key(row_name)
                
                # Normalize year suffix if present
                final_pred = None
                if pred:
                    if pred in catalog:
                        final_pred = pred
                    elif pred.replace('_2023', '') in catalog:
                        final_pred = pred.replace('_2023', '')
                
                # Cache the result (even if None, to avoid re-querying)
                _AI_CACHE[row_name] = final_pred
                
                if final_pred:
                    return final_pred

    # 3. Legacy Regex Fallback (Keep as safety net)
    # Normalize
    row_name_norm = normalize_text(row_name)
    name_tokens = set(row_name_norm.split())
    
    row_full_norm = normalize_text(f"{row_name} {row_specs}")
    full_tokens = set(row_full_norm.split())
    row_full_lower = row_full_norm.lower()

    best_key = None
    best_score = (-1, 0) # (from_name, token_len)

    for key, info in catalog.items():
        cat_name = normalize_text(info['name'])
        cat_tokens = set(cat_name.split())
        category = info.get('category', 'Unknown')
        
        # --- NEGATIVE CHECKS (Prevent Cross-Category Matches) ---
        if category == 'Watch':
            if any(x in row_full_lower for x in ['ipad', 'iphone', 'macbook', 'imac', 'airpods', 'tai nghe', 'mac mini']):
                continue
        elif category == 'iPad':
            if any(x in row_full_lower for x in ['iphone', 'watch', 'macbook', 'imac', 'airpods', 'tai nghe', 'mac mini']):
                continue
        elif category == 'iPhone':
            if any(x in row_full_lower for x in ['ipad', 'watch', 'macbook', 'imac', 'airpods', 'tai nghe', 'mac mini']):
                continue
        elif category == 'Audio':
             if any(x in row_full_lower for x in ['ipad', 'iphone', 'watch', 'macbook', 'imac', 'mac mini']):
                continue
        elif category == 'Mac':
             if any(x in row_full_lower for x in ['ipad', 'iphone', 'watch', 'airpods', 'tai nghe']):
                # Be careful, Macs might be bundled, but usually main product logic applies
                continue
        
        # Check if catalog has keywords (for special matching like AirPods)
        keywords = info.get('keywords', [])
        keyword_match = False
        
        if keywords:
            # Check if ANY keyword appears in the full text
            for keyword in keywords:
                keyword_norm = normalize_text(str(keyword)).lower()
                # Enhanced Keyword Check: strict boundary or containment
                if keyword_norm in row_full_lower:
                    keyword_match = True
                    break
        
        # 1. Must be subset of FULL tokens OR have keyword match
        if not (cat_tokens.issubset(full_tokens) or keyword_match):
            continue
            
        # 2. Metrics
        is_name_subset = cat_tokens.issubset(name_tokens)
        cat_len = len(cat_tokens)
        
        # Score priority:
        # 1. Keyword match gets bonus (2 for keyword, 1 for name, 0 for specs only)
        # 2. Length of tokens (Specificity)
        match_type = 0
        if keyword_match:
            match_type = 2  # Highest priority for keyword match
        elif is_name_subset:
            match_type = 1
        
        current_score = (match_type, cat_len)
        
        if current_score > best_score:
            best_score = current_score
            best_key = key
            
    return best_key

def extract_extra_specs(text, exclude_storage=None):
    """
    Extract RAM only (not CPU/GPU) to avoid inconsistency across retailers.
    CPU/GPU specs are model-dependent and don't help differentiate products.
    """
    text = text.lower()
    details = []
    
    # Extract RAM only
    ram_match = re.search(r'\b(8|12|16|18|24|32|36|48|64|96|128)\s*gb\b', text)
    if ram_match:
        val = f"{ram_match.group(1)}gb"
        # Skip if this matches the storage value (prevents duplication)
        if exclude_storage and val == exclude_storage.lower():
             pass
        else:
             details.append(f"{ram_match.group(1)}GB") 
    
    # NOTE: CPU/GPU extraction removed to ensure consistent product names
    # across retailers for accurate price comparison.
    # Example: "MacBook Pro 14 M5 16GB/512GB" should always map to same name
    # whether retailer mentions "10CPU 10GPU" or not.
    
    return " ".join(details)


def standardize_attributes(product_key, raw_text, catalog, color_aliases=None):
    """
    Extract Standard Attributes (Color, Storage, Size) based on Catalog definitions.
    Uses regex and fuzzy matching against the Valid Value Lists in Catalog.
    """
    info = catalog.get(product_key, {})
    valid_colors = info.get('colors', [])
    valid_storage = info.get('storage', [])
    valid_sizes = info.get('sizes', [])
    valid_conn = info.get('connectivity', [])
    
    std_attrs = {
        'color': "Unknown",
        'storage': None,
        'size': None,
        'connectivity': None,
        'band': None
    }
    
    raw_lower = normalize_text(raw_text)
    
    # 1. Size Matching
    # Extract number + unit (mm, inch)
    # Check if that roughly matches any valid size
    for vs in valid_sizes:
        # vs might be "42mm" or "13.6 inch"
        # Extract numeric part
        num_match = re.match(r'([0-9\.,]+)', vs)
        if num_match:
            num = num_match.group(1)
            # Match number, optionally followed by space, then optionally unit (mm, inch, ", m)
            # OR just ensure the number exists with boundary or unit.
            # Retailer: "42mm", "42 mm", "13.6 inch", "13.6inch", "13.6\""
            # Regex: \bNUMBER\s*(mm|inch|in|"|”)?
            # But "42mm" has no boundary after 2.
            # So search for NUMBER literal, followed by optional unit.
            regex = re.escape(num) + r"\s*(mm|inch|in|\"|”|$|\s)"
            if re.search(regex, raw_lower):
                 std_attrs['size'] = vs
                 break
                 
    # 2. Connectivity Matching
    # Logic: If 'cellular'/'5g'/'lte' -> prefer "GPS + Cellular" or "Wi-Fi + Cellular" if available
    # If just 'gps' -> "GPS"
    # If 'wifi' -> "Wi-Fi"
    is_cell = any(x in raw_lower for x in ['cellular', 'lte', '5g', '4g'])
    is_gps = 'gps' in raw_lower
    
    if valid_conn:
        if is_cell:
            # Find the option with "Cellular"
            for vc in valid_conn:
                if 'Cellular' in vc:
                    std_attrs['connectivity'] = vc
                    break
        elif is_gps:
             # Find option with "GPS" but NOT Cellular (if possible, or just GPS)
             # If only "GPS + Cellular" exists (e.g. Stainless Steel), use that? 
             # No, if it's steel it MUST be cellular. Catalog enforces it.
             # So if catalog only has "GPS + Cellular", we use it even if retailer says GPS (implies GPS+Cell)
             if len(valid_conn) == 1:
                 std_attrs['connectivity'] = valid_conn[0]
             else:
                 # Prefer simple GPS
                 for vc in valid_conn:
                     if 'GPS' in vc and 'Cellular' not in vc:
                         std_attrs['connectivity'] = vc
                         break
    
    # 3. Color Matching (Enhanced with Aliases)
    # 3.1 Extract raw color candidate from text (simple extraction logic)
    # This is hard because color can be anywhere. 
    # Instead, we iterate over known aliases + catalog colors to find matches.
    
    found_color = None
    
    # helper to check if a word is in text
    def has_word(word, text):
        # simple word boundary check
        return re.search(r'\b' + re.escape(word.lower()) + r'\b', text)

    # 3.2 Check Product-Specific Overrides first (Highest Priority)
    if color_aliases and 'product_overrides' in color_aliases:
        overrides = color_aliases['product_overrides'].get(product_key, {})
        for raw_col, map_col in overrides.items():
            if has_word(raw_col, raw_lower):
                found_color = map_col
                break
                
    # 3.3 Check Global Aliases (Medium Priority)
    if not found_color and color_aliases and 'global_aliases' in color_aliases:
        # Sort keys by length desc to match "Xanh Dương" before "Xanh"
        for raw_col in sorted(color_aliases['global_aliases'].keys(), key=len, reverse=True):
            if has_word(raw_col, raw_lower):
                 mapped = color_aliases['global_aliases'][raw_col]
                 if mapped: # if not null
                     found_color = mapped
                     break
                 
    # 3.4 Fallback to Catalog Colors (Exact Match)
    if not found_color:
        for vc in valid_colors:
            if has_word(vc, raw_lower):
                found_color = vc
                break
                
    # 3.5 Fallback to Fuzzy Token Match (Lowest Priority)
    if not found_color:
        raw_tokens = set(re.split(r'\W+', raw_lower))
        best_color = None
        best_overlap = 0 # Need at least 2 tokens overlap if color name is long, or 1 if short
        
        for vc in valid_colors:
            vc_tokens = set(re.split(r'\W+', vc.lower()))
            overlap = len(raw_tokens.intersection(vc_tokens))
            
            # Penalize generic matches like just "Màu" or "Sắc" if they existed
            if overlap > best_overlap:
                best_overlap = overlap
                best_color = vc
        
        if best_color and best_overlap >= 1: 
             found_color = best_color

    if found_color:
        std_attrs['color'] = found_color

    # 4. Band Types (Not in Catalog, keep custom logic)
    bands = []
    if 'dây cao su' in raw_lower or 'rubber' in raw_lower or 'sport band' in raw_lower: bands.append("Dây Cao Su")
    if 'dây vải' in raw_lower or 'sport loop' in raw_lower or 'fabric' in raw_lower: bands.append("Dây Vải")
    if 'milan' in raw_lower: bands.append("Dây Milanese")
    if 'alpine' in raw_lower: bands.append("Dây Alpine")
    if 'ocean' in raw_lower: bands.append("Dây Ocean")
    if 'trail' in raw_lower: bands.append("Dây Trail")
    if bands:
        std_attrs['band'] = " + ".join(bands)
        
    return std_attrs

def process_csv_files(quiet=False):
    catalog = load_catalog()
    retailer_mapping = load_retailer_mapping()
    color_aliases = load_color_aliases()
    all_data = []
    unmatched_data = []  # Track products that don't match catalog
    
    csv_files = glob.glob(str(CONTENT_DIR / "*.csv"))
    
    for f in csv_files:
        filename = os.path.basename(f)
        retailer_key = "-".join(filename.split('-')[:2])
        if retailer_key not in RETAILER_MAP:
             for k in RETAILER_MAP:
                 if k in filename:
                     retailer_key = k
                     break
        
        retailer_name = RETAILER_MAP.get(retailer_key, "Unknown")
        if not quiet:
            print(f"Processing {retailer_name} from {filename}...")
        
        try:
            try:
                df = pd.read_csv(f, sep=';', on_bad_lines='skip')
            except:
                df = pd.read_csv(f, sep=',', on_bad_lines='skip')
            
            col_map = {
                'Gia_Khuyen_Mai': 'Price', 'price': 'Price',
                'Product_Name': 'Name', 'name': 'Name',
                'Color': 'Color', 'Link': 'URL',
                'Ton_Kho': 'Stock', 'stock': 'Stock',
                'Tech_Specs': 'Specs', 'Thong_So_Ky_Thuat': 'Specs',
                'Khuyen_Mai': 'Promotion Details', 'promotion_details': 'Promotion Details',
                'Thanh_Toan': 'Payment Promo', 'payment_promo': 'Payment Promo',
                'Uu_Dai_Them': 'Payment Promo', # MW uses this
                'Voucher_Image': 'Voucher', 'voucher': 'Voucher',
                'Other_promotion': 'Other Promo', 'other_promo': 'Other Promo'
            }
            df.rename(columns=col_map, inplace=True)
            
            if 'Price' not in df.columns or 'Name' not in df.columns:
                continue
                
            for _, row in df.iterrows():
                raw_name = row['Name']
                raw_specs = str(row.get('Specs', '')).strip()
                if raw_specs == 'nan': raw_specs = ''
                raw_color = str(row.get('Color', '')).strip()
                raw_full = f"{raw_name} {raw_color} {raw_specs}"

                raw_price = row['Price']
                raw_stock = str(row.get('Stock', 'yes')).lower().strip()
                # Determine stock status (Yes/No)
                stock_status = 'No' if raw_stock in ['no', 'false', '0', 'hết hàng', 'out of stock'] else 'Yes'

                price = clean_price(raw_price)
                
                # For in-stock products, require valid price
                # For OOS products, allow price=0 or None
                if stock_status == 'Yes':
                    if not price or price < 100000: 
                        continue  # Skip in-stock products without valid price
                # OOS products can have price=0 or None, we keep them
                
                prod_key = match_product(raw_name, raw_specs, catalog, retailer_name, retailer_mapping)
                
                if prod_key:
                    storage = normalize_storage(raw_name)
                    if storage == "unknown_storage": storage = normalize_storage(raw_specs)

                    # Standardize Attributes (Color, Storage, Size)
                    std_attrs = standardize_attributes(prod_key, f"{raw_name} {raw_specs} {raw_color}", catalog, color_aliases)
                    cat_name = catalog[prod_key]['name']
                    category = catalog[prod_key]['category']
                    
                    # Extract extra details (RAM, etc.) early
                    other_details = extract_extra_specs(raw_full, exclude_storage=storage) 
                    
                    # --- Category-Specific Name Construction ---
                    parts = [cat_name]
                    
                    # Helper to check redundancy against dynamic current name
                    def is_redundant(val):
                        if not val: return True
                        current_text = " ".join(parts).lower()
                        # Check strictly for the value boundary
                        val_cleaned = str(val).lower().replace('(', '').replace(')', '')
                        return val_cleaned in current_text

                    # 1. Mac: Name + RAM + Color + Storage
                     # 1. Mac: Name + RAM + Storage + Color
                    if category == 'Mac':
                         # RAM (from other_details, excluding storage)
                         if other_details and not is_redundant(other_details):
                             parts.append(other_details)
                         
                         # Storage
                         if storage and storage != 'unknown_storage' and not is_redundant(storage):
                             parts.append(storage)

                         # Color
                         if std_attrs['color'] and std_attrs['color'] != "Unknown" and not is_redundant(std_attrs['color']):
                             parts.append(std_attrs['color'])

                    # 2. Watch: Name + Band + Color
                    elif category == 'Watch':
                         # Band
                         if std_attrs['band'] and not is_redundant(std_attrs['band']):
                             parts.append(std_attrs['band'])
                         
                         # Color (Case/Band Color)
                         if std_attrs['color'] and std_attrs['color'] != "Unknown" and not is_redundant(std_attrs['color']):
                             parts.append(std_attrs['color'])
                             
                         # No storage for watches usually

                    # 3. Audio / Accessories: Name + Color
                    elif category in ['Audio', 'Accessories']:
                         if std_attrs['color'] and std_attrs['color'] != "Unknown" and not is_redundant(std_attrs['color']):
                             parts.append(std_attrs['color'])

                    # 4. Default (iPhone, iPad): Name + Color + Storage
                    # 4. Default (iPhone, iPad): Name + Storage + Color
                    else:
                         # Storage
                         if storage and storage != 'unknown_storage' and not is_redundant(storage):
                             parts.append(storage)

                         # Color
                         if std_attrs['color'] and std_attrs['color'] != "Unknown" and not is_redundant(std_attrs['color']):
                             parts.append(std_attrs['color'])
                        
                    rich_name = " ".join(parts)
                    rich_name = re.sub(r'\s+', ' ', rich_name).strip()

                    all_data.append({
                        'retailer': retailer_name,
                        'original_name': raw_name,
                        'original_specs': raw_specs[:100],
                        'product_key': prod_key,
                        'product_name': rich_name,
                        'category': category,
                        'variant_storage': storage if storage != 'unknown_storage' else '',
                        'variant_color': std_attrs['color'] if std_attrs['color'] != 'Unknown' else '',
                        'price': price,
                        'stock': stock_status,  # Include stock status (Yes/No)
                        'url': row.get('URL', ''),
                        'Promotion Details': row.get('Promotion Details', ''),
                        'Payment Promo': row.get('Payment Promo', ''),
                        'Other Promo': row.get('Other Promo', ''),
                        'Voucher': row.get('Voucher', '')
                    })
                else:
                    # Track unmatched products
                    unmatched_data.append({
                        'retailer': retailer_name,
                        'original_name': raw_name,
                        'original_specs': raw_specs[:100] if raw_specs else '',
                        'price': price if price else 0,
                        'stock': stock_status,
                        'url': row.get('URL', '')
                    })
                    
        except Exception as e:
            print(f"Error processing {f}: {e}")


    return pd.DataFrame(all_data), pd.DataFrame(unmatched_data)


def process_date_data(date_str):
    """
    Process raw CSV files for a specific date and return normalized data.
    Does not save output - used for loading historical data on-the-fly.
    """
    global CONTENT_DIR
    original_content_dir = CONTENT_DIR
    
    try:
        # Set CONTENT_DIR for this specific date
        CONTENT_DIR = CONTENT_BASE / date_str
        
        if not CONTENT_DIR.exists():
            return pd.DataFrame(), pd.DataFrame()
        
        # Process without verbose output (quiet mode)
        df, df_unmatched = process_csv_files(quiet=True)
        return df, df_unmatched
        
    finally:
        # Restore original CONTENT_DIR
        CONTENT_DIR = original_content_dir


# ============================================================
# TREND ANALYSIS HELPER FUNCTIONS
# ============================================================

def load_historical_data(days=30, verbose=False):
    """
    Load and normalize raw data from data/raw/ for the past N days.
    Processes on-the-fly without depending on pre-generated clean_data files.
    """
    all_data = []
    
    # Get available date folders from data/raw/
    available_dates = sorted(get_available_dates())[-days:]
    
    if not available_dates:
        if verbose:
            print("No date folders found in data/raw/")
        return pd.DataFrame()
    
    if verbose:
        print(f"📊 Loading {len(available_dates)} days of historical data...")
    
    for i, date_str in enumerate(available_dates):
        try:
            # Process raw data for this date (reuse existing function)
            df_clean, _ = process_date_data(date_str)
            
            if not df_clean.empty:
                df_clean['date'] = date_str
                all_data.append(df_clean)
                
            if verbose and (i + 1) % 10 == 0:
                print(f"  Processed {i + 1}/{len(available_dates)} days...")
                
        except Exception as e:
            if verbose:
                print(f"  Error processing {date_str}: {e}")
            
    if all_data:
        combined = pd.concat(all_data, ignore_index=True)
        combined['date'] = pd.to_datetime(combined['date'])
        if verbose:
            print(f"✅ Loaded {len(combined)} records from {len(available_dates)} days")
        return combined
    return pd.DataFrame()


def detect_anomalies(df_today, df_historical, group_cols, threshold=0.10):
    """
    Detect price anomalies: today's price vs 7-day moving average
    Returns DataFrame of products with significant deviations
    """
    if df_historical.empty:
        return pd.DataFrame()
    
    # Calculate 7-day average per group
    avg_7d = df_historical.groupby(group_cols)['price'].mean().reset_index()
    avg_7d.rename(columns={'price': 'avg_7d'}, inplace=True)
    
    # Merge with today's data
    merged = pd.merge(df_today, avg_7d, on=group_cols, how='inner')
    
    # Calculate deviation
    merged['deviation_pct'] = ((merged['price'] - merged['avg_7d']) / merged['avg_7d']) * 100
    
    # Filter anomalies (>threshold deviation, either direction)
    anomalies = merged[abs(merged['deviation_pct']) > (threshold * 100)].copy()
    
    # Add type label
    anomalies['type'] = anomalies['deviation_pct'].apply(
        lambda x: '📉 GIẢM' if x < 0 else '📈 TĂNG'
    )
    
    return anomalies.sort_values('deviation_pct')


def calculate_trend(df_historical, group_cols, days=30):
    """
    Calculate price trend using linear regression over N days
    Returns DataFrame with trend info per product group
    """
    if df_historical.empty:
        return pd.DataFrame()
    
    # Filter to last N days
    max_date = df_historical['date'].max()
    cutoff = max_date - timedelta(days=days)
    recent = df_historical[df_historical['date'] >= cutoff].copy()
    
    if recent.empty:
        return pd.DataFrame()
    
    # Get daily average price per group, include product_name for display
    daily = recent.groupby(group_cols + ['date']).agg(
        price=('price', 'mean'),
        url=('url', 'first'),
        product_name=('product_name', 'first'),  # Add for display
        category=('category', 'first'),
        variant_color=('variant_color', 'first')
    ).reset_index()
    
    results = []
    for name, group in daily.groupby(group_cols):
        if len(group) < 3:  # Need at least 3 data points
            continue
        
        group = group.sort_values('date')
        x = np.arange(len(group))
        y = group['price'].values
        
        try:
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
            
            # Calculate % change:
            # - For Drops: Compare Current Price vs MAX Price in period (User Request)
            # - For Increases: Compare Current Price vs MIN Price in period (to see true hikes)
            # This avoids "Start Price" bias if start price was high/low
            
            max_price = np.max(y)
            min_price = np.min(y)
            current_price = y[-1]
            
            # Default to Start vs End logic
            pct_change = ((current_price - y[0]) / y[0]) * 100 if y[0] != 0 else 0
            
            # Refined Logic for Drop Detection
            drop_from_peak = ((current_price - max_price) / max_price) * 100 if max_price != 0 else 0
            increase_from_bottom = ((current_price - min_price) / min_price) * 100 if min_price != 0 else 0
            
            # Decide which metric to show
            # Determine dates for display
            last_date = group.iloc[-1]['date']
            
            if drop_from_peak < -5:
                trend = "🔻 Giảm"
                display_pct = drop_from_peak
                base_price = max_price
                # Find date of max price
                base_date = group[group['price'] == max_price].iloc[0]['date']
            elif increase_from_bottom > 5:
                trend = "🔺 Tăng"
                display_pct = increase_from_bottom
                base_price = min_price
                # Find date of min price
                base_date = group[group['price'] == min_price].iloc[0]['date']
            else:
                trend = "➡️ Ổn định"
                display_pct = pct_change
                base_price = y[0]
                base_date = group.iloc[0]['date']
            
            # Format dates (YYYY-MM-DD -> DD/MM/YYYY)
            def fmt_date(d): return pd.to_datetime(d).strftime('%d/%m/%Y')

            row = {col: val for col, val in zip(group_cols, name if isinstance(name, tuple) else [name])}
            row.update({
                'trend': trend,
                'pct_change': round(display_pct, 1),
                'r_squared': round(r_value**2, 2),
                'first_price': base_price,
                'last_price': current_price,
                'base_date_str': fmt_date(base_date),
                'last_date_str': fmt_date(last_date),
                'url': group.iloc[-1]['url'],
                'product_name': group.iloc[-1]['product_name'],
                'category': group.iloc[-1]['category'],
                'variant_color': group.iloc[-1]['variant_color'],
                'max_price': max_price
            })
            results.append(row)
        except Exception:
            continue
    
    return pd.DataFrame(results)


def generate_insights(df):
    """
    Generate daily price insights with proper deduplication.
    Groups by product_key + variant_storage to ensure consistency across retailers.
    """
    # Filter OUT of stock products for insights ONLY
    df_in_stock = df[df['stock'] == 'Yes'].copy()
    
    if df_in_stock.empty:
        return "# 📊 Daily Price Insights\n\n⚠️ No in-stock products found.\n"
    
    s = f"# 📊 Daily Price Insights - {datetime.date.today()}\n\n"
    s += f"*Generated at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
    s += f"*Showing only **IN-STOCK** products ({len(df_in_stock)} out of {len(df)} total)*\n\n"
    
    # Helper: Get canonical product name for display
    def get_display_name(row):
        """
        Return the pre-calculated rich product name.
        (Color/Storage are already included in product_name by normalize.py)
        """
        return row.get('product_name', 'Unknown')
    
    # ============================================================
    # 1. BEST PRICES (Top 15 Deals) - Deduplicated by product_key
    # ============================================================
    # ============================================================
    # 1. BEST PRICES PER MODEL (Grouped by Category)
    # ============================================================
    s += "## 💰 GIÁ TỐT NHẤT (Theo Dòng Máy)\n"
    s += "_Giá thấp nhất ghi nhận được cho từng dòng sản phẩm (In-Stock Only)_\n\n"
    
    # Define Category Order
    cat_order = ['iPhone', 'iPad', 'Mac', 'Watch', 'Audio', 'Accessories']
    
    # Calculate min price per product_key (Model Level)
    # We want the absolute lowest price for "iPhone 16 Pro Max" regardless of color/storage?
    # No, usually "Best Price" for a model implies the base model (cheapest storage/color).
    # So we group by product_key and find min price row.
    
    min_prices_idx = df_in_stock.groupby('product_key')['price'].idxmin()
    best_models = df_in_stock.loc[min_prices_idx].copy()
    
    # Sort by Category Order then Price Descending (Flagships first)
    best_models['cat_rank'] = best_models['category'].map({c: i for i, c in enumerate(cat_order)}).fillna(99)
    best_models = best_models.sort_values(by=['cat_rank', 'price'], ascending=[True, False])
    
    # Group by Category for Display
    for cat in cat_order:
        cat_models = best_models[best_models['category'] == cat]
        if cat_models.empty: continue
        
        # Icon mapping
        icon = ""
        if cat == 'iPhone': icon = "📱"
        elif cat == 'iPad': icon = "🖊️"
        elif cat == 'Mac': icon = "💻"
        elif cat == 'Watch': icon = "⌚"
        elif cat in ['Audio', 'Accessories']: icon = "🎧"
        
        s += f"### {icon} {cat}\n"
        
        for _, row in cat_models.iterrows():
            price_fmt = "{:,.0f}đ".format(row['price'])
            
            # For display, we want just the Model Name mostly, but 'product_name' includes color/storage.
            # We should probably use the Catalog Name or clean up the product_name to be just the Model?
            # User wants "iPhone 16 Pro Max", "iPhone 16".
            # Currently 'product_name' is "iPhone 16 Pro Max 256GB Titan Sa Mạc".
            # We can try to extract the base Model Name from Catalog if available, or just use product_key logic.
            # Actually, `product_name` is constructed in `process_csv_files`. 
            # Let's try to show the full name of the cheapest variant found, so user knows WHICH one is cheap.
            # e.g. "iPhone 16 Pro Max 256GB Titan: 28.9m"
            
            display = get_display_name(row)
            s += f"- **{display}**: **{price_fmt}** @ **{row['retailer']}** [Link]({row['url']})\n"
        s += "\n"
    
    # ============================================================
    # 2. PRICE VARIATION (Retailer vs Market Average)
    # ============================================================
    s += "## ⚠️ BIẾN ĐỘNG GIÁ (vs Giá Trung Bình)\n"
    
    # Calculate average price per product/storage
    avg_prices = df_in_stock.groupby(['product_key', 'variant_storage'])['price'].mean().reset_index()
    avg_prices.rename(columns={'price': 'avg_price'}, inplace=True)
    
    merged_var = pd.merge(df_in_stock, avg_prices, on=['product_key', 'variant_storage'])
    merged_var['diff_pct'] = ((merged_var['price'] - merged_var['avg_price']) / merged_var['avg_price']) * 100
    
    # Filter significant deals (>10% below average)
    deals = merged_var[merged_var['diff_pct'] < -10].copy()
    
    # Deduplicate by product/storage/retailer
    deals = deals.drop_duplicates(subset=['product_key', 'variant_storage', 'retailer']).sort_values('diff_pct').head(15)
    
    if len(deals) > 0:
        for _, row in deals.iterrows():
            price_fmt = "{:,.0f}đ".format(row['price'])
            avg_fmt = "{:,.0f}đ".format(row['avg_price'])
            display = get_display_name(row)
            s += f"- 📉 **{row['retailer']}** bán **{display}** giá **{price_fmt}** ({row['diff_pct']:.1f}% so với TB {avg_fmt}) [Link]({row['url']})\n"
    else:
        s += "_Không có sản phẩm giá thấp hơn đáng kể so với thị trường._\n"
    s += "\n"
    
    # ============================================================
    # TREND ANALYSIS SECTIONS (using historical data)
    # ============================================================
    df_historical = load_historical_data(days=30, verbose=True)
    
    if not df_historical.empty:
        df_hist_instock = df_historical[df_historical['stock'] == 'Yes'].copy()
        
        if not df_hist_instock.empty:
            max_date = df_hist_instock['date'].max()
            cutoff_7d = max_date - timedelta(days=7)
            df_7d = df_hist_instock[df_hist_instock['date'] >= cutoff_7d]
            
            # --- 3. ANOMALIES - THỊ TRƯỜNG (vs 7-day avg) ---
            s += "## 📊 BIẾN ĐỘNG BẤT THƯỜNG - THỊ TRƯỜNG (vs 7 ngày)\n"
            
            market_anomalies = detect_anomalies(
                df_in_stock, df_7d, 
                ['product_key', 'variant_storage'],  # Fixed: use product_key
                threshold=0.10
            )
            
            if len(market_anomalies) > 0:
                # Deduplicate
                market_anomalies = market_anomalies.drop_duplicates(
                    subset=['product_key', 'variant_storage']
                ).head(10)
                
                for _, row in market_anomalies.iterrows():
                    price_fmt = "{:,.0f}đ".format(row['price'])
                    display = get_display_name(row)
                    s += f"- {row['type']} **{display}**: {row['deviation_pct']:+.1f}% → {price_fmt} [Link]({row['url']})\n"
            else:
                s += "_Không phát hiện biến động bất thường._\n"
            s += "\n"
            
            # --- 4. ANOMALIES - TỪNG CHUỖI ---
            s += "## 🏪 BIẾN ĐỘNG BẤT THƯỜNG - TỪNG CHUỖI (vs 7 ngày)\n"
            
            store_anomalies = detect_anomalies(
                df_in_stock, df_7d,
                ['retailer', 'product_key', 'variant_storage'],  # Fixed
                threshold=0.10
            )
            
            if len(store_anomalies) > 0:
                store_anomalies = store_anomalies.drop_duplicates(
                    subset=['retailer', 'product_key', 'variant_storage']
                ).head(15)
                
                for _, row in store_anomalies.iterrows():
                    display = get_display_name(row)
                    s += f"- {row['type']} [{row['retailer']}] **{display}**: {row['deviation_pct']:+.1f}% [Link]({row['url']})\n"
            else:
                s += "_Không phát hiện biến động bất thường._\n"
            s += "\n"
            
            # --- 5. XU HƯỚNG 7 NGÀY - THỊ TRƯỜNG ---
            s += "## 📈 XU HƯỚNG 7 NGÀY - THỊ TRƯỜNG\n"
            
            market_trends_7 = calculate_trend(df_hist_instock, ['product_key', 'variant_storage'], days=7)
            
            if len(market_trends_7) > 0:
                big_movers = market_trends_7[abs(market_trends_7['pct_change']) > 5].sort_values('pct_change').head(10)
                for _, row in big_movers.iterrows():
                    display = get_display_name(row)
                    s += f"- {row['trend']} **{display}**: {row['pct_change']:+.1f}% ({row['base_date_str']}: {row['first_price']:,.0f}đ → {row['last_date_str']}: {row['last_price']:,.0f}đ) [Link]({row['url']})\n"
            else:
                s += "_Chưa đủ dữ liệu để phân tích xu hướng 7 ngày._\n"
            s += "\n"
            
            # --- 6. XU HƯỚNG 7 NGÀY - TỪNG CHUỖI ---
            s += "## 🏪 XU HƯỚNG 7 NGÀY - TỪNG CHUỖI\n"
            
            store_trends_7 = calculate_trend(df_hist_instock, ['retailer', 'product_key', 'variant_storage'], days=7)
            
            if len(store_trends_7) > 0:
                big_store_movers = store_trends_7[abs(store_trends_7['pct_change']) > 10].sort_values('pct_change').head(15)
                for _, row in big_store_movers.iterrows():
                    display = get_display_name(row)
                    s += f"- {row['trend']} [{row['retailer']}] **{display}**: {row['pct_change']:+.1f}% ({row['base_date_str']}: {row['first_price']:,.0f}đ → {row['last_date_str']}: {row['last_price']:,.0f}đ) [Link]({row['url']})\n"
            else:
                s += "_Chưa đủ dữ liệu để phân tích xu hướng 7 ngày._\n"
            s += "\n"
            
            # --- 7. XU HƯỚNG 30 NGÀY - THỊ TRƯỜNG ---
            s += "## 📈 XU HƯỚNG 30 NGÀY - THỊ TRƯỜNG\n"
            
            market_trends_30 = calculate_trend(df_hist_instock, ['product_key', 'variant_storage'], days=30)
            
            if len(market_trends_30) > 0:
                big_movers_30 = market_trends_30[abs(market_trends_30['pct_change']) > 5].sort_values('pct_change').head(10)
                for _, row in big_movers_30.iterrows():
                    display = get_display_name(row)
                    s += f"- {row['trend']} **{display}**: {row['pct_change']:+.1f}% ({row['base_date_str']}: {row['first_price']:,.0f}đ → {row['last_date_str']}: {row['last_price']:,.0f}đ) [Link]({row['url']})\n"
            else:
                s += "_Chưa đủ dữ liệu để phân tích xu hướng 30 ngày._\n"
            s += "\n"
            
            # --- 8. XU HƯỚNG 30 NGÀY - TỪNG CHUỖI ---
            s += "## 🏪 XU HƯỚNG 30 NGÀY - TỪNG CHUỖI\n"
            
            store_trends_30 = calculate_trend(df_hist_instock, ['retailer', 'product_key', 'variant_storage'], days=30)
            
            if len(store_trends_30) > 0:
                big_store_movers_30 = store_trends_30[abs(store_trends_30['pct_change']) > 10].sort_values('pct_change').head(15)
                for _, row in big_store_movers_30.iterrows():
                    display = get_display_name(row)
                    s += f"- {row['trend']} [{row['retailer']}] **{display}**: {row['pct_change']:+.1f}% ({row['base_date_str']}: {row['first_price']:,.0f}đ → {row['last_date_str']}: {row['last_price']:,.0f}đ) [Link]({row['url']})\n"
            else:
                s += "_Chưa đủ dữ liệu để phân tích xu hướng 30 ngày._\n"
            s += "\n"
    else:
        s += "\n_Không có dữ liệu lịch sử để phân tích xu hướng._\n"
    
    s += "---\n"
    s += f"*Data sources: {df_in_stock['retailer'].nunique()} retailers, {len(df_in_stock)} in-stock records (excluded {len(df) - len(df_in_stock)} OOS products).*\n"
    
    return s


def get_available_dates():
    """Scan content directory for date folders (YYYY-MM-DD format)"""
    dates = []
    date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    
    for entry in CONTENT_BASE.iterdir():
        if entry.is_dir() and date_pattern.match(entry.name):
            dates.append(entry.name)
    
    return sorted(dates)

def main(target_date=None, process_all=False):
    """Process CSVs for specific date or all dates
    
    Args:
        target_date: Specific date string (YYYY-MM-DD) or None for latest
        process_all: If True, process all available dates
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    INSIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    
    available_dates = get_available_dates()
    
    if not available_dates:
        print(f"❌ No date folders found in {CONTENT_BASE}")
        return
    
    # Determine which dates to process
    if process_all:
        dates_to_process = available_dates
        print(f"📅 Processing all {len(dates_to_process)} dates...")
    elif target_date:
        if target_date in available_dates:
            dates_to_process = [target_date]
            print(f"📅 Processing specific date: {target_date}")
        else:
            print(f"❌ Date {target_date} not found in content directory")
            return
    else:
        # Default: process latest date only
        dates_to_process = [available_dates[-1]]
        print(f"📅 Processing latest date: {dates_to_process[0]}")
    
    # Process each date
    for date_str in dates_to_process:
        print(f"\n{'='*60}")
        print(f"Processing date: {date_str}")
        print(f"{'='*60}")
        
        # Set CONTENT_DIR globally for this iteration
        global CONTENT_DIR
        CONTENT_DIR = CONTENT_BASE / date_str
        
        print("Normalizing data via Product Name...")
        df, df_unmatched = process_csv_files()
        
        if not df.empty:
            # Save clean data (Renamed from normalized_mapping for clarity)
            out_csv = OUTPUT_DIR / f"clean_data_{date_str}.csv"
            df.to_csv(out_csv, index=False)
            print(f"✅ Saved clean data to {out_csv}")
            
            # Save unmatched products to LOGS directory
            if not df_unmatched.empty:
                unmatched_csv = LOGS_DIR / f"unmatched_err_{date_str}.csv"
                df_unmatched.to_csv(unmatched_csv, index=False)
                print(f"⚠️  Saved {len(df_unmatched)} unmatched errors to {unmatched_csv}")
                
                # Summary by retailer and stock status
                print(f"\n📋 Unmatched Products Summary:")
                summary = df_unmatched.groupby(['retailer', 'stock']).size().reset_index(name='count')
                for _, row in summary.iterrows():
                    print(f"   - {row['retailer']}: {row['count']} products (stock={row['stock']})")
            
            # Generate Insights
            print("\nGenerating insights...")
            markdown = generate_insights(df)
            
            insights_file = INSIGHTS_DIR / f"{date_str}_insights_v2.md"
            with open(insights_file, 'w') as f:
                f.write(markdown)
                
            print(f"✅ Saved insights to {insights_file}")
        else:
            print(f"⚠️ No matches found for {date_str}. Check matching logic.")

if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Normalize product data')
    parser.add_argument('date', nargs='?', help='Target date (YYYY-MM-DD)')
    parser.add_argument('--all', action='store_true', help='Process all dates')
    parser.add_argument('--no-ai', action='store_true', help='Disable AI fallback (for CI/CD)')
    args = parser.parse_args()
    
    # Set global AI flag
    if args.no_ai:
        AI_ENABLED = False
        print("⚠️ AI fallback disabled (--no-ai flag)")
    
    if args.all:
        main(process_all=True)
    elif args.date:
        main(target_date=args.date)
    else:
        main()  # Latest date only
