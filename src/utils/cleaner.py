
import re
import pandas as pd

def clean_price(price):
    val = None
    if pd.isna(price): return None
    
    if isinstance(price, (int, float)):
        val = float(price)
    else:
        s = str(price)
        # Clean standard delimiters
        s_clean = re.sub(r'[.,]', '', s) 
        
        # Find all groups of digits
        matches = re.findall(r'\d+', s_clean)
        if not matches: return None
        
        for m in matches:
            v = float(m)
            if v > 100000 and v < 200000000: 
                 val = v
                 break
    
    if val and 100000 < val < 200000000:
        return val
    return None

def normalize_text(text):
    text = str(text).lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def normalize_storage(name):
    name = name.lower()
    matches = re.findall(r'(\d+)\s*(gb|tb)', name)
    
    if not matches:
        return "unknown_storage"
        
    for val_str, unit in matches:
        val = int(val_str)
        size_gb = val * 1024 if unit == 'tb' else val
        
        # Filter RAM sizes
        if size_gb in [4, 6, 8, 12, 18, 24, 36, 40, 48, 96]:
            continue
            
        return f"{val}{unit}"
        
    return "unknown_storage"
