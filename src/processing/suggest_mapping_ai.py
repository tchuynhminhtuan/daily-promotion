
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
ADAPTER_PATH = BASE_DIR / "experiments/fine_tuning/adapters_llama"
BASE_MODEL = "mlx-community/Llama-3.2-3B-Instruct-4bit"

# ... (omitted shared code)

def ai_predict(model, tokenizer, product_name):
    SYSTEM_PROMPT = "You are a product matching assistant. Map the retailer product name to the correct canonical key."
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Map this product: {product_name}"}
    ]
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    
    response = generate(model, tokenizer, prompt=prompt, max_tokens=20, verbose=False)
    return response.strip()

# ...

def main():
    # ...
    # 3. Load AI Model
    print(f"🤖 Loading Llama 3B from {ADAPTER_PATH}...")
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
            
            # VALIDATION CHECK
            if predicted_key not in canonical_keys:
                # Try simple normalization or fuzzy fix?
                # Or try to fix _lte suffix if hallucinated?
                # For now, just mark invalid to prevent crash
                # Maybe map to 'nan' or skip
                print(f"   ⚠️ Invalid Key Predict: '{predicted_key}' (Not in Catalog)")
                # suggestions[retailer][p_name] = f"FIXME: {predicted_key}"
                continue
            
            suggestions[retailer][p_name] = predicted_key
            print(f"   '{p_name}' -> {predicted_key}")

    # 5. Save Report
    if not suggestions:
        print("No valid suggestions generated.")
        return

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("# AI Generated Suggestions (Review before merging)\n")
        yaml.dump(suggestions, f, allow_unicode=True, sort_keys=False)
        
    print(f"✅ Suggestions saved to {OUTPUT_FILE}")
    print("👉 Review this file, then copy correct entries to catalog/retailer_mapping.yaml")

if __name__ == "__main__":
    main()
