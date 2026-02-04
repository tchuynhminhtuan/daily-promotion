
import src.utils.config as config
from src.utils.cleaner import normalize_text

_AI_CACHE = {} 
_AI_MODEL = None
_AI_TOKENIZER = None

def load_ai_model():
    global _AI_MODEL, _AI_TOKENIZER
    if _AI_MODEL is None:
        try:
            from mlx_lm import load
            print(f"🤖 Loading Llama 3B from {config.AI_MODEL_PATH}...")
            _AI_MODEL, _AI_TOKENIZER = load(config.BASE_MODEL_ID, adapter_path=str(config.AI_MODEL_PATH))
        except Exception as e:
            print(f"⚠️ Failed to load AI model: {e}")
            return False
    return True

def ai_predict_key(product_name):
    # Only use AI if enabled
    if not config.AI_ENABLED: return None
    
    if not load_ai_model(): return None
    
    # Check cache first
    if product_name in _AI_CACHE:
        return _AI_CACHE[product_name]

    # Use globals loaded by load_ai_model
    model, tokenizer = _AI_MODEL, _AI_TOKENIZER
    if not model: return None
    
    try:
        from mlx_lm import generate
        # ... logic ...
        SYSTEM_PROMPT = "You are a product matching assistant. Map the retailer product name to the correct canonical key."
        
        # New Chat Template for Llama 3 (V3)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Map this product: {product_name}"}
        ]
        prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        
        response = generate(model, tokenizer, prompt=prompt, max_tokens=20, verbose=False)
        pred_key = response.strip()
        
        # Hybrid Rules (Same as Benchmark)
        p_lower = product_name.lower()
        if "gps" in p_lower and "lte" not in p_lower and "cellular" not in p_lower:
            pred_key = pred_key.replace("_lte", "_gps").replace("_cellular", "_gps").replace("_gps_gps", "_gps")
        if "wifi" in p_lower and "5g" not in p_lower:
             pred_key = pred_key.replace("_5g", "").replace("_lte", "").replace("_cellular", "")
        
        # Cache result
        _AI_CACHE[product_name] = pred_key
        return pred_key
    except Exception as e:
        print(f"AI Error: {e}")
        return None

def extract_extra_specs(text, exclude_storage=None):
    specs = []
    text_lower = text.lower()
    
    # Extract RAM (Skip if it matches storage or is standard 8GB/16GB if ambiguous)
    # This is tricky without more context, but let's try basic RAM patterns
    ram_match = re.search(r'(\d+)\s*(gb|ram)', text_lower)
    if ram_match:
        val = int(ram_match.group(1))
        # Logic to differentiate RAM vs Storage?
        # Usually handled by specific catalog rules or placement
        pass 
    return specs

def standardize_attributes(product_key, raw_text, catalog, color_aliases=None):
    # This function relies on the Catalog definition to extract valid Colors, Capacities for the matched Product
    if product_key not in catalog:
        return None, None
    
    product_info = catalog[product_key]
    valid_colors = product_info.get('colors', [])
    valid_storage = product_info.get('storage', [])
    
    text_norm = normalize_text(raw_text)
    
    # 1. Extract Storage
    found_storage = None
    if valid_storage:
        # Check against valid catalog entries first (Exact Match)
        for s in valid_storage:
            # normalize s (e.g. "1TB" -> "1tb")
            if s.lower() in text_norm:
                found_storage = s
                break
        
        # If not found, try regex extraction
        if not found_storage:
           # Fallback logic
           pass

    # 2. Extract Color
    found_color = None
    if valid_colors:
        # Check aliases first if provided
        # Then check exact color names
        for c in valid_colors:
             if c.lower() in text_norm:
                 found_color = c
                 break

    # 3. Extract Size (e.g., 40mm, 44mm, 11 inch, 12.9 inch)
    # Regex for sizes
    import re
    found_size = None
    size_match = re.search(r'(\d+)\s*(mm|inch|inh|")', text_norm)
    if size_match:
        # Standardize inch to "inch"
        unit = size_match.group(2)
        val = size_match.group(1)
        if unit in ['"', 'inh']: unit = 'inch'
        found_size = f"{val}{unit}"
    
    # 4. Extract Connectivity (WiFi, 5G, GPS, LTE)
    found_conn = []
    if 'wifi' in text_norm: found_conn.append('WiFi')
    if '5g' in text_norm: found_conn.append('5G')
    if '4g' in text_norm or 'lte' in text_norm: found_conn.append('4G')
    if 'gps' in text_norm: found_conn.append('GPS')
    if 'cellular' in text_norm: found_conn.append('Cellular')
    # Deduplicate/Prioritize: usually "WiFi + 5G"
    found_connectivity = " + ".join(sorted(list(set(found_conn)))) if found_conn else None

    # 5. Extract Band (for Watches) - Generic fallback
    found_band = None
    if 'dây' in text_norm or 'band' in text_norm:
        # Simple extraction: "Dây cao su", "Dây vải"
        # Match "dây" followed by 2-3 words
        band_match = re.search(r'(dây\s+\w+(\s+\w+)?)', text_norm)
        if band_match:
             found_band = band_match.group(1).title()

    return {
        'color': found_color if found_color else "Unknown",
        'storage': found_storage if found_storage else "Unknown",
        'size': found_size if found_size else "",
        'connectivity': found_connectivity if found_connectivity else "",
        'band': found_band if found_band else ""
    }

def match_product(row_name, row_specs, catalog, retailer_name=None, retailer_mapping=None):
    """
    Smart Matching Logic:
    1. Direct Mapping (Retailer Map)
    2. Smart Score (Fuzzy Match + Specs)
    3. AI Fallback (Llama 3B)
    """
    
    # 1. Direct Mapping (Fastest & Most Accurate)
    if retailer_mapping:
        retailer_key = retailer_name or "unknown"
        # Logic to lookup in mapping dict
        # ...
        pass
        
    # 2. Smart Match
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
        
        # Check if catalog has keywords (for special matching like AirPods)
        keywords = info.get('keywords', [])
        keyword_match = False
        
        if keywords:
            # Check if ANY keyword appears in the full text
            for keyword in keywords:
                keyword_norm = normalize_text(str(keyword)).lower()
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
            
    if best_key:
        return best_key, "smart_match"
    ai_key = ai_predict_key(row_name)
    if ai_key and ai_key in catalog:
        return ai_key, "ai_match"
        
    return None, "unmatched"
