
import glob
import pandas as pd
import yaml
from pathlib import Path
from mlx_lm import load, generate

# Configuration
BASE_DIR = Path(".")
DATA_DIR = BASE_DIR / "data/raw"
MAPPING_PATH = BASE_DIR / "catalog/retailer_mapping.yaml"
OUTPUT_FILE = BASE_DIR / "catalog/ai_suggested_mapping.yaml"
ADAPTER_PATH = BASE_DIR / "experiments/fine_tuning/adapters"
BASE_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"

def load_existing_mapping():
    if not MAPPING_PATH.exists():
        return set()
    with open(MAPPING_PATH, 'r') as f:
        data = yaml.safe_load(f)
    
    mapped_names = set()
    for retailer in data:
        for name in data[retailer]:
            mapped_names.add(name)
    return mapped_names

def find_unmapped_products(mapped_names):
    csv_files = glob.glob(str(DATA_DIR / "**/*.csv"), recursive=True)
    unmapped = {} # {retailer: {name: 1}} using dict for uniqueness
    
    print(f"🔍 Scanning {len(csv_files)} CSV files for unmapped products...")
    
    for file in csv_files:
        try:
            df = pd.read_csv(file)
            # Identify columns
            name_col = next((c for c in df.columns if 'name' in c.lower()), None)
            retailer_col = next((c for c in df.columns if 'retailer' in c.lower()), None)
            
            if not name_col: continue
            
            # Default retailer from filename if missing
            retailer = "Unknown"
            filename = Path(file).name.lower()
            if 'cps' in filename: retailer = "cellphones"
            elif 'viettel' in filename: retailer = "viettel_store"
            elif 'mw' in filename or 'tgdd' in filename: retailer = "mobile_world"
            elif 'fpt' in filename: retailer = "fpt_shop"
            elif 'hoangha' in filename: retailer = "hoangha_mobile"
            elif 'ddv' in filename: retailer = "didongviet"

            for _, row in df.iterrows():
                p_name = str(row[name_col]).strip()
                p_retailer = row[retailer_col] if retailer_col and pd.notna(row[retailer_col]) else retailer
                
                # Normalize retailer key to match yaml format
                p_retailer_key = p_retailer.lower().replace(" ", "_")
                
                if p_name not in mapped_names:
                    if p_retailer_key not in unmapped:
                        unmapped[p_retailer_key] = {}
                    unmapped[p_retailer_key][p_name] = True
                    
        except Exception as e:
            # print(f"Error reading {file}: {e}")
            continue
            
    total_unmapped = sum(len(x) for x in unmapped.values())
    print(f"⚠️ Found {total_unmapped} unique unmapped products.")
    return unmapped

def ai_predict(model, tokenizer, product_name):
    SYSTEM_PROMPT = "You are a product matching assistant. Map the retailer product name to the correct canonical key."
    prompt = f"<|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>\n<|im_start|>user\nMap this product: {product_name}<|im_end|>\n<|im_start|>assistant\n"
    
    response = generate(model, tokenizer, prompt=prompt, max_tokens=20, verbose=False)
    return response.strip()

def main():
    # 1. Load what we already know
    mapped_names = load_existing_mapping()
    
    # 2. Find what we don't know
    unmapped_data = find_unmapped_products(mapped_names)
    
    if not unmapped_data:
        print("🎉 No unmapped products found!")
        return

    # 3. Load AI Model
    print(f"🤖 Loading Qwen 0.5B from {ADAPTER_PATH}...")
    try:
        model, tokenizer = load(BASE_MODEL, adapter_path=str(ADAPTER_PATH))
    except Exception as e:
        print(f"❌ Failed to load model: {e}")
        print("Did you run the fine-Tuning experiment first?")
        return

    # 4. Predict
    suggestions = {}
    print("🔮 Predicting mappings...")
    
    for retailer, products in unmapped_data.items():
        print(f"Processing {retailer} ({len(products)} items)...")
        suggestions[retailer] = {}
        for p_name in products:
            predicted_key = ai_predict(model, tokenizer, p_name)
            suggestions[retailer][p_name] = predicted_key
            print(f"   '{p_name}' -> {predicted_key}")

    # 5. Save Report
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("# AI Generated Suggestions (Review before merging)\n")
        yaml.dump(suggestions, f, allow_unicode=True, sort_keys=False)
        
    print(f"✅ Suggestions saved to {OUTPUT_FILE}")
    print("👉 Review this file, then copy correct entries to catalog/retailer_mapping.yaml")

if __name__ == "__main__":
    main()
