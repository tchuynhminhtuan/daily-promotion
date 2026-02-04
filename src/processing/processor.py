
import os
import glob
import pandas as pd
from datetime import datetime
from src.utils.config import CONTENT_DIR, OUTPUT_DIR, LOGS_DIR, RETAILER_MAP, load_catalog, load_retailer_mapping, load_color_aliases
from src.utils.cleaner import clean_price, normalize_text, normalize_storage
from src.matching.engine import match_product, standardize_attributes, extract_extra_specs

def process_csv_files(quiet=False):
    catalog = load_catalog()
    color_aliases = load_color_aliases()
    retailer_mapping = load_retailer_mapping()
    
    # Reload AI model if needed (usually handled in main or on demand)
    
    # Find all CSV files for TODAY (or specifically target date in main)
    # But this function seems designed to process *latest* or specific folders?
    # Original code scanned CONTENT_DIR recursively? 
    # Let's adapt to receive a list of files or date, but original code used glob.
    pass 

# Refactored Version: process_date_data covers most of this.
# process_csv_files in original code was doing "Load ALL from ALL dates??" No, let's look at logic.
# It iterated glob(CONTENT_DIR / "*/*.csv"). That's expensive.
# process_date_data(date_str) is better.

def process_date_data(date_str, output_csv=True):
    date_path = CONTENT_DIR / date_str
    if not date_path.exists():
        print(f"Directory not found: {date_path}")
        return pd.DataFrame(), pd.DataFrame()
    
    csv_files = glob.glob(str(date_path / "*.csv"))
    if not csv_files:
        print(f"No CSV files found in {date_path}")
        return pd.DataFrame(), pd.DataFrame()
        
    print(f"\nExample Processing for {date_str}...")
    
    catalog = load_catalog()
    retailer_mapping = load_retailer_mapping()
    color_aliases = load_color_aliases()
    
    all_data = []
    unmatched = []
    
    for f in csv_files:
        filename = os.path.basename(f)
        retailer_key = filename.split('-')[1] if '-' in filename else 'unknown'
        retailer_name = RETAILER_MAP.get(f"{filename.split('-')[0]}-{retailer_key}", retailer_key)
        
        try:
            # Smart CSV Read
            try:
                df = pd.read_csv(f, sep=',', on_bad_lines='skip', engine='python')
                if len(df.columns) < 2: # Probe for semicolon
                     df = pd.read_csv(f, sep=';', on_bad_lines='skip', engine='python')
            except:
                continue

            for _, row in df.iterrows():
                # Normalize Columns
                name = str(row.get('Name', row.get('Product_Name', ''))).strip()
                price = clean_price(row.get('Price', row.get('Gia_Khuyen_Mai', row.get('Gia_Niem_Yet', 0))))
                link = row.get('Link', '')
                stock_status = str(row.get('Stock_Status', row.get('Stock', ''))).lower()
                is_stock = 'hết hàng' not in stock_status and 'out' not in stock_status and 'contact' not in stock_status
                
                if not name or not price: continue
                
                # Match
                specs_text = str(row.get('Specs', ''))
                color_text = str(row.get('Color', ''))
                
                match_key, method = match_product(name, specs_text, catalog, retailer_name, retailer_mapping)
                
                if match_key:
                    # Standardization
                    # Pass full text including explicit Color column to ensure attribute extraction finds it
                    full_desc = f"{name} {specs_text} {color_text}"
                    std_attrs = standardize_attributes(match_key, full_desc, catalog, color_aliases)
                    
                    # Add Category & Name
                    category = catalog[match_key].get('category', 'Unknown')
                    catalog_name = catalog[match_key].get('name', match_key)
                    
                    # Construct rich name (simplified)
                    full_name = catalog_name
                    if std_attrs['connectivity']: full_name += f" ({std_attrs['connectivity']})"
                    if std_attrs['storage'] and std_attrs['storage'] != 'Unknown': full_name += f" {std_attrs['storage']}"
                    if std_attrs['color'] and std_attrs['color'] != 'Unknown': full_name += f" {std_attrs['color']}"
                    
                    item = {
                        'date': date_str,
                        'retailer': retailer_name,
                        'product_key': match_key,
                        'product_name': full_name,
                        'category': category,
                        'variant_color': std_attrs['color'],
                        'variant_storage': std_attrs['storage'],
                        'variant_size': std_attrs['size'],
                        'variant_connectivity': std_attrs['connectivity'],
                        'band': std_attrs['band'],
                        'price': price,
                        'stock': 'Yes' if is_stock else 'No',
                        'url': link,
                        'original_name': name,
                        'method': method
                    }
                    all_data.append(item)
                else:
                    unmatched.append({
                        'retailer': retailer_name,
                        'name': name,
                        'price': price,
                        'stock': 'Yes' if is_stock else 'No'
                    })
                    
        except Exception as e:
            print(f"Error processing {filename}: {e}")

    # Save Results
    df_norm = pd.DataFrame(all_data)
    
    if output_csv:
        output_file = OUTPUT_DIR / f"clean_data_{date_str}.csv"
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        df_norm.to_csv(output_file, index=False)
        print(f"✅ Saved clean data to {output_file}")
        
    # Save Unmatched
    if unmatched:
        log_file = LOGS_DIR / f"unmatched_err_{date_str}.csv"
        os.makedirs(LOGS_DIR, exist_ok=True)
        pd.DataFrame(unmatched).to_csv(log_file, index=False)
        print(f"⚠️  Saved {len(unmatched)} unmatched errors to {log_file}")
        
    return df_norm, pd.DataFrame(unmatched)
