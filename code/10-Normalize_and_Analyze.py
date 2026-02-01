
import pandas as pd
import yaml
import glob
import re
import os
import datetime
from pathlib import Path

# Config
BASE_DIR = Path("/Users/brucehuynh/GitHub/daily-promotion")
CATALOG_PATH = BASE_DIR / "product_catalog_golden_v2.yaml"
CONTENT_BASE = BASE_DIR / "content"  # Base directory, will scan for dates
OUTPUT_DIR = BASE_DIR / "analysis/normalized"
INSIGHTS_DIR = BASE_DIR / "docs/insights"

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
    return f"{best_val}{best_unit}"

# New Config
MAPPING_PATH = BASE_DIR / "analysis/reference/retailer_mapping_v1.yaml"

def load_retailer_mapping():
    if not os.path.exists(MAPPING_PATH): return {}
    with open(MAPPING_PATH, 'r') as f:
        return yaml.safe_load(f)

def match_product(row_name, row_specs, catalog, retailer_name=None, retailer_mapping=None):
    # 1. Exact Match via Retailer Mapping (Priority)
    if retailer_name and retailer_mapping and retailer_name in retailer_mapping:
         mapped_key = retailer_mapping[retailer_name].get(str(row_name).strip())
         if mapped_key:
             return mapped_key

    # Normalize
    row_name_norm = normalize_text(row_name)
    name_tokens = set(row_name_norm.split())
    
    row_full_norm = normalize_text(f"{row_name} {row_specs}")
    full_tokens = set(row_full_norm.split())

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
            row_full_lower = row_full_norm.lower()
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


def standardize_attributes(product_key, raw_text, catalog):
    """
    Map extracted attributes from raw_text to permissible values in catalog[product_key].
    Returns a dict of standard attributes.
    """
    entry = catalog.get(product_key, {})
    valid_sizes = entry.get('sizes', []) or []
    valid_colors = entry.get('colors', []) or []
    # valid_storage = entry.get('storage', []) or [] # Storage usually handled by normalize_storage
    valid_conn = entry.get('connectivity', []) or []
    
    raw_lower = raw_text.lower()
    std_attrs = {
        'size': None,
        'connectivity': None,
        'color': None,
        'band': None # Band is usually not in catalog, treat separately
    }
    
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
    
    # 3. Color Matching (Fuzzy)
    # Retailer might say "Đen", Catalog has "Nhôm Đen Bóng" or "Titan Đen"
    # We prioritize the color that contains the retailer's word
    # Also extracted raw_color from previous steps might help.
    # Here we search for keywords in raw_text against valid_colors
    
    # Basic token set match
    raw_tokens = set(re.split(r'\W+', raw_lower))
    best_color = None
    best_overlap = 0
    
    for vc in valid_colors:
        vc_tokens = set(re.split(r'\W+', vc.lower()))
        overlap = len(raw_tokens.intersection(vc_tokens))
        if overlap > best_overlap:
            best_overlap = overlap
            best_color = vc
            
    if best_color and best_overlap >= 1: # At least one word matches (e.g. "Bạc")
        std_attrs['color'] = best_color

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

def process_csv_files():
    catalog = load_catalog()
    retailer_mapping = load_retailer_mapping()
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
                'Tech_Specs': 'Specs', 'Thong_So_Ky_Thuat': 'Specs'
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

                    # Standardize Attributes using Catalog
                    std_attrs = standardize_attributes(prod_key, raw_full, catalog)
                    cat_name = catalog[prod_key]['name']
                    
                    # Construction: Name + Size + Connectivity + Color + Storage + Band
                    parts = [cat_name]
                    
                    if std_attrs['size']: parts.append(std_attrs['size'])
                    if std_attrs['connectivity']: parts.append(f"({std_attrs['connectivity']})") # User liked parens (GPS)
                    if std_attrs['color']: parts.append(std_attrs['color'])
                    
                    # Storage
                    if storage != 'unknown_storage': parts.append(storage)
                    
                    # Band
                    if std_attrs['band']: parts.append(std_attrs['band'])
                    
                    # Extracted Details fallback (RAM, etc if not covered)?
                    # For Macs, we might want RAM/CPU.
                    # Re-use extract_extra_specs() for non-watch items?
                    # Let's keep extract_extra_specs for "Other Specs" like RAM/CPU
                    other_details = extract_extra_specs(raw_full, exclude_storage=storage) 
                    if other_details: parts.append(other_details)
                        
                    rich_name = " ".join(parts)
                    rich_name = re.sub(r'\s+', ' ', rich_name).strip()

                    all_data.append({
                        'retailer': retailer_name,
                        'original_name': raw_name,
                        'original_specs': raw_specs[:100],
                        'product_key': prod_key,
                        'product_name': rich_name,
                        'category': catalog[prod_key]['category'],
                        'variant_storage': storage,
                        'variant_color': std_attrs['color'] or raw_color,
                        'price': price,
                        'stock': stock_status,  # Include stock status (Yes/No)
                        'url': row.get('URL', '')
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


def generate_insights(df):
    # Filter OUT of stock products for insights ONLY
    df_in_stock = df[df['stock'] == 'Yes'].copy()
    
    if df_in_stock.empty:
        return "# 📊 Daily Price Insights\n\n⚠️ No in-stock products found.\n"
        
    s = f"# 📊 Daily Price Insights - {datetime.date.today()}\n\n"
    s += f"*Generated at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
    s += f"*Showing only **IN-STOCK** products ({len(df_in_stock)} out of {len(df)} total)*\n\n"
    
    # 1. BEST PRICE EVER (Min Price per Product/Storage)
    s += "## 💰 BEST PRICES (Top 15 Deals)\n"
    
    idx = df_in_stock.groupby(['product_key', 'variant_storage'])['price'].idxmin()
    best_prices = df_in_stock.loc[idx].sort_values('price').head(20) # Show top 20 cheap to expensive?
    best_prices = best_prices.sort_values(['category', 'product_name'])
    
    for _, row in best_prices.iterrows():
        price_fmt = "{:,.0f}đ".format(row['price'])
        s += f"- **{row['product_name']} ({row['variant_storage']})** ({row['variant_color']}) @ **[{row['retailer']}]**: **{price_fmt}** [Link]({row['url']})\n"
        
    s += "\n"
    
    # 2. Anomalies (Price Difference vs Average)
    s += "## ⚠️ PRICE VARIATION (Retailer vs Average)\n"
    
    avg_prices = df_in_stock.groupby(['product_key', 'variant_storage'])['price'].mean().reset_index()
    avg_prices.rename(columns={'price': 'avg_price'}, inplace=True)
    
    merged = pd.merge(df_in_stock, avg_prices, on=['product_key', 'variant_storage'])
    merged['diff_pct'] = ((merged['price'] - merged['avg_price']) / merged['avg_price']) * 100
    
    deals = merged[merged['diff_pct'] < -10].sort_values('diff_pct')
    
    deal_count = 0
    for _, row in deals.iterrows():
        if deal_count >= 20: break
        
        price_fmt = "{:,.0f}đ".format(row['price'])
        avg_fmt = "{:,.0f}đ".format(row['avg_price'])
        s += f"- 📉 **{row['retailer']}** sells **{row['product_name']} ({row['variant_storage']})** for **{price_fmt}** ({row['diff_pct']:.1f}% below avg {avg_fmt}) [Link]({row['url']})\n"
        deal_count += 1
        
    s += "\n---\n"
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
        
        print("Normalizing data via Product Name + Tech Specs...")
        df, df_unmatched = process_csv_files()
        
        if not df.empty:
            # Save normalized CSV with date from folder (not today's date)
            out_csv = OUTPUT_DIR / f"normalized_mapping_{date_str}.csv"
            df.to_csv(out_csv, index=False)
            print(f"✅ Saved mapping file to {out_csv}")
            
            # Save unmatched products for review
            if not df_unmatched.empty:
                unmatched_csv = OUTPUT_DIR / f"unmatched_products_{date_str}.csv"
                df_unmatched.to_csv(unmatched_csv, index=False)
                print(f"⚠️  Saved {len(df_unmatched)} unmatched products to {unmatched_csv}")
                
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
    
    # Command line arguments:
    # python 10-Normalize_and_Analyze.py              # Process latest date
    # python 10-Normalize_and_Analyze.py 2026-01-31   # Process specific date
    # python 10-Normalize_and_Analyze.py --all        # Process all dates
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--all":
            main(process_all=True)
        else:
            main(target_date=sys.argv[1])
    else:
        main()  # Latest date only
