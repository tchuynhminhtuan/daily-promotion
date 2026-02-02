
"""
Generate Training Data for Fine-Tuning
Extracts high-quality product mapping pairs from historical data.

Output Format (JSONL):
{"messages": [{"role": "user", "content": "Map: iPhone 13 Pro Max 128GB VN/A"}, {"role": "assistant", "content": "iphone_13_pro_max"}]}
"""

import pandas as pd
import json
import re
from pathlib import Path
from collections import Counter
import sys
import yaml

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))
import src.processing.normalize as normalize_module
# Disable AI for training data generation (Ground Truth from Rules)
normalize_module.AI_ENABLED = False
from src.processing.normalize import match_product, normalize_text, load_catalog

BASE_DIR = Path("/Users/brucehuynh/GitHub/daily-promotion")
OUTPUT_FILE = BASE_DIR / "experiments/fine_tuning/data/training_data_v2.jsonl"
OUTPUT_DIR = OUTPUT_FILE.parent

def load_historical_raw_data():
    """Load all raw CSV files similar to analyze_price_trends.py"""
    all_data = []
    
    # 1. Load from data/raw/
    raw_dir = BASE_DIR / "data/raw"
    for date_dir in sorted(raw_dir.glob("202*")):
        if date_dir.is_dir():
            for csv_file in date_dir.glob("*.csv"):
                try:
                    df = pd.read_csv(csv_file, sep=';', on_bad_lines='skip')
                    if 'Product_Name' in df.columns:
                        all_data.append(df)
                except:
                    pass

    # 2. Load from Market Promotion/ (legacy)
    legacy_dir = BASE_DIR / "Market Promotion"
    for csv_file in legacy_dir.rglob("*.csv"):
        try:
             # Try common separators
            for sep in [';', ',', '\t']:
                try:
                    df = pd.read_csv(csv_file, sep=sep, on_bad_lines='skip')
                    if 'Product_Name' in df.columns:
                         # Normalize columns
                        df.columns = [c.strip() for c in df.columns]
                        all_data.append(df)
                        break
                except:
                    continue
        except:
            pass

    if all_data:
        return pd.concat(all_data, ignore_index=True)
    return pd.DataFrame()

def generate_dataset():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("🔄 Loading historical data...")
    df = load_historical_raw_data()
    
    if df.empty:
        print("❌ No data found")
        return

    print(f"📊 Total records loaded: {len(df):,}")
    
    # Load catalog for validation
    catalog = load_catalog()
    
    # Track unique pairs to avoid duplicates in training data
    # Key: (Raw Name, Raw Specs) -> Value: Canonical Key
    dataset_pairs = {}
    
    print("🔍 Processing and matching products...")
    
    # Pre-compile regex for speed
    spam_keywords = ["giảm", "ưu đãi", "thanh toán", "thẻ tín dụng", "vnpay", "hoàn tiền", "chính sách", "liên hệ", "trả góp", "quà tặng", "v ch"]
    
    count = 0
    skipped_spam = 0
    skipped_low_price = 0
    skipped_no_match = 0
    
    # Iterate with progress
    unique_inputs = df[['Product_Name', 'Tech_Specs', 'Gia_Khuyen_Mai']].drop_duplicates()
    
    print(f"⚡ Unique inputs to process: {len(unique_inputs):,}")
    
    for _, row in unique_inputs.iterrows():
        raw_name = str(row['Product_Name']).strip()
        raw_specs = str(row['Tech_Specs']).strip()
        if raw_specs == 'nan': raw_specs = ''
        
        # 1. Filter: Price (Skip accessories/spam < 100k)
        try:
            price = float(row['Gia_Khuyen_Mai'])
            if price < 100000:
                skipped_low_price += 1
                continue
        except:
            continue
            
        # 2. Filter: Spam keywords
        name_lower = raw_name.lower()
        if any(k in name_lower for k in spam_keywords):
            skipped_spam += 1
            continue
            
        # 3. Match Logic (Strict)
        # We use match_product BUT we need to ensure it's a high quality match.
        # Ideally, we rely on the deterministic logic in match_product (Catalog containment)
        
        # Disable AI for generating training data (we want Ground Truth from rules)
        # Note: We must trust our current rule-based system as the "Teacher"
        match_key = match_product(raw_name, raw_specs, catalog)
        
        if match_key:
            # Create training sample
            # Input: "iPhone 13 Pro Max 128GB VN/A"
            # Output: "iphone_13_pro_max"
            
            # Use a clean input string
            input_text = raw_name
            if len(raw_specs) > 0 and len(raw_specs) < 50:
                 input_text += f" {raw_specs}"
            
            # Store in dictionary to deduplicate
            if input_text not in dataset_pairs:
                dataset_pairs[input_text] = match_key
        else:
            skipped_no_match += 1
            if skipped_no_match <= 20:
                print(f"   [DEBUG] No Match: {raw_name} | {raw_specs}")
            
        count += 1
        if count % 5000 == 0:
            print(f"   Processed {count}/{len(unique_inputs)} records... (Pairs: {len(dataset_pairs)})")
            sys.stdout.flush()

    print(f"\n✅ Generated {len(dataset_pairs):,} unique training pairs")
    print(f"   Skipped (Spam): {skipped_spam}")
    print(f"   Skipped (Low Price): {skipped_low_price}")
    print(f"   Skipped (No Match): {skipped_no_match}")
    
    # Write to JSONL
    print(f"\n💾 Saving to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for text, label in dataset_pairs.items():
            sample = {
                "messages": [
                    {"role": "user", "content": f"Map this product: {text}"},
                    {"role": "assistant", "content": label}
                ]
            }
            f.write(json.dumps(sample, ensure_ascii=False) + '\n')
            
    print("✨ Done!")

if __name__ == "__main__":
    generate_dataset()
