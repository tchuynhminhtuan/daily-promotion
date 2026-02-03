
import glob
import pandas as pd
import yaml
import json
import random
import sys
from pathlib import Path
from collections import defaultdict

# Add Src to Path to import normalize
BASE_DIR = Path(".")
sys.path.append(str(BASE_DIR / "src"))
from processing.normalize import load_catalog, match_product

# Configuration
DATA_DIR = BASE_DIR / "data/raw"
MAPPING_PATH = BASE_DIR / "catalog/retailer_mapping.yaml"
OUTPUT_DIR = BASE_DIR / "experiments/fine_tuning/data"
OUTPUT_FILE = OUTPUT_DIR / "train.jsonl"
VALID_FILE_AUG = OUTPUT_DIR / "valid.jsonl"

def load_existing_mapping():
    with open(MAPPING_PATH, 'r') as f:
        data = yaml.safe_load(f)
    pairs = []
    for ret, prods in data.items():
        for name, key in prods.items():
            pairs.append({"input": name, "output": key, "source": "manual"})
    return pairs

def generate_from_raw():
    catalog = load_catalog() # Load catalog definitions
    csv_files = glob.glob(str(DATA_DIR / "**/*.csv"), recursive=True)
    csv_files += glob.glob("data/raw_legacy/*.csv")
    
    generated_data = []
    seen_inputs = set()
    
    print(f"🔍 Scanning {len(csv_files)} CSVs for auto-labeling...")
    
    for file in csv_files:
        try:
            # Try sniffing separator or use engine python
            df = pd.read_csv(file, sep=None, engine='python')
            
            name_col = next((c for c in df.columns if 'name' in c.lower()), None)
            price_col = next((c for c in df.columns if 'price' in c.lower()), None)
            
            if not name_col: continue

            for _, row in df.iterrows():
                p_name = str(row[name_col]).strip()
                
                # Filter Garbage
                if price_col:
                    try:
                        val = float(str(row[price_col]).replace('.', '').replace(',', '').replace('đ', '').strip() or 0)
                        if val < 100000: continue
                    except: continue
                
                spam = ["giảm", "ưu đãi", "thanh toán", "thẻ tín dụng", "liên hệ"]
                if any(x in p_name.lower() for x in spam): continue
                if len(p_name) > 150: continue

                # Dedup
                if p_name in seen_inputs: continue

                # Auto-Label using Rule-Based Matcher
                product_key = match_product(p_name, {}, catalog)
                
                if product_key:
                    generated_data.append({"input": p_name, "output": product_key, "source": "auto"})
                    seen_inputs.add(p_name)
                    
        except Exception as e:
            print(f"Error processing {file}: {e}")
            continue
            
    return generated_data

def generate_synthetic_data(catalog):
    """
    Generate synthetic variations for ALL products to ensure balanced coverage.
    Solves the bias issue where rare products (e.g. SE 3 LTE 44mm) have no training data.
    """
    print("🧪 Generating synthetic data for balanced coverage...")
    synthetic_samples = []
    
    # Common noise words in retailer titles
    prefixes = ["Điện thoại", "Máy tính bảng", "Laptop", "Đồng hồ", "Tai nghe", "Apple", "Mua ngay"]
    suffixes = ["Chính hãng", "VN/A", "Giá rẻ", "Trả góp 0%", "Mới 100%", "Nguyên seal"]
    
    for key, info in catalog.items():
        base_name = info.get('name', '')
        category = info.get('category', 'Unknown')
        
        # Skip if no name
        if not base_name: continue
        
        # Generate variations
        variations = [
            base_name, # Raw name
            base_name.lower(), # Lowercase
            f"{base_name} VN/A", # Common suffix
            f"Apple {base_name}", # Common prefix
        ]
        
        # Add color/storage permutations if available
        colors = info.get('colors', [])
        storages = info.get('storage', [])
        
        # Pick random combos to avoid explosion, but ensure at least 5 samples per key
        for _ in range(10):
            p = random.choice(prefixes) if random.random() > 0.5 else ""
            s = random.choice(suffixes) if random.random() > 0.5 else ""
            c = random.choice(colors) if colors else ""
            st = random.choice(storages) if storages else ""
            
            # Construct noisy title
            # e.g. "Điện thoại iPhone 13 128GB Xanh VN/A"
            components = [p, base_name, st, c, s]
            # Shuffle slightly? No, word order usually fixed.
            
            full_name = " ".join([x for x in components if x]).strip()
            variations.append(full_name)
            
        for v in variations:
            synthetic_samples.append({"input": v, "output": key, "source": "synthetic"})
            
    return synthetic_samples

def main():
    # 1. Load Manual Labels (High Quality)
    manual_data = load_existing_mapping()
    print(f"✅ Loaded {len(manual_data)} manual mappings.")
    
    # 2. Generate Auto Labels (Medium Quality but Huge Quantity)
    auto_data = generate_from_raw()
    print(f"✅ Generated {len(auto_data)} auto-labeled mappings from history.")
    
    # 3. Merge & Balance
    # We want to oversample manual data to ensure high priority
    final_dataset = []
    
    # Add manual data 10 times (High Priority)
    for _ in range(10):
        final_dataset.extend(manual_data)
            
    # Add synthetic data 5 times (Medium Priority - Coverage)
    synthetic_data = generate_synthetic_data(load_catalog())
    for _ in range(5):
        final_dataset.extend(synthetic_data)
        
    print(f"✅ Generated {len(synthetic_data)} synthetic balanced samples.")

    # Add auto data once (Low Priority - Volume)
    final_dataset.extend(auto_data)
    
    print(f"📊 Total Training Samples: {len(final_dataset)}")
    
    # 4. Format for Chat Template
    chat_dataset = []
    SYSTEM_PROMPT = "You are a product matching assistant. Map the retailer product name to the correct canonical key."

    for item in final_dataset:
        entry = {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Map this product: {item['input']}"},
                {"role": "assistant", "content": item['output']}
            ]
        }
        chat_dataset.append(entry)
        
    # 5. Split & Save
    random.shuffle(chat_dataset)
    split = int(len(chat_dataset) * 0.95)
    train = chat_dataset[:split]
    valid = chat_dataset[split:]
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for x in train: f.write(json.dumps(x, ensure_ascii=False) + "\n")
        
    with open(VALID_FILE_AUG, 'w', encoding='utf-8') as f:
        for x in valid: f.write(json.dumps(x, ensure_ascii=False) + "\n")
        
    print(f"💾 Saved {len(train)} training samples to {OUTPUT_FILE}")
    print(f"💾 Saved {len(valid)} validation samples to {VALID_FILE_AUG}")

if __name__ == "__main__":
    main()
