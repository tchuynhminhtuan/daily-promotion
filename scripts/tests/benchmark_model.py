
import yaml
import random
import time
from pathlib import Path
from mlx_lm import load, generate
from tqdm import tqdm

# Configuration
BASE_DIR = Path(".")
MAPPING_PATH = BASE_DIR / "catalog/retailer_mapping.yaml"
ADAPTER_PATH = BASE_DIR / "experiments/fine_tuning/adapters"
BASE_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
SAMPLE_SIZE = 100

def load_ground_truth():
    with open(MAPPING_PATH, 'r') as f:
        data = yaml.safe_load(f)
    
    pairs = [] # (Retailer, ProductName, TrueKey)
    for retailer, products in data.items():
        for name, key in products.items():
            pairs.append((retailer, name, key))
            
    print(f"📊 Total defined mappings: {len(pairs)}")
    return pairs

def ai_predict(model, tokenizer, product_name):
    SYSTEM_PROMPT = "You are a product matching assistant. Map the retailer product name to the correct canonical key."
    prompt = f"<|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>\n<|im_start|>user\nMap this product: {product_name}<|im_end|>\n<|im_start|>assistant\n"
    
    response = generate(model, tokenizer, prompt=prompt, max_tokens=20, verbose=False)
    pred_key = response.strip()

    # --- HYBRID RULES (Post-Processing) ---
    p_lower = product_name.lower()
    
    # Rule 1: GPS vs LTE Enforcement
    if "gps" in p_lower and "lte" not in p_lower and "cellular" not in p_lower:
        if "_lte" in pred_key or "_cellular" in pred_key:
            # Force replace lte -> gps (rudimentary fix) or just strip it
            pred_key = pred_key.replace("_lte", "_gps").replace("_cellular", "_gps")
            # If replacement resulted in duplicate _gps_gps, fix it
            pred_key = pred_key.replace("_gps_gps", "_gps")
            
    # Rule 2: Wifi Enforcement
    if "wifi" in p_lower and "5g" not in p_lower:
        if "_5g" in pred_key or "_lte" in pred_key or "_cellular" in pred_key:
             # Strip connectivity suffix if it wrongly guessed 5G
             pred_key = pred_key.replace("_5g", "").replace("_lte", "").replace("_cellular", "")
             # Add _wifi if needed? Or rely on default.
             # Ideally validation mapping should handle this, but for now let's just remove the wrong tag.

    return pred_key

def main():
    # 1. Prepare Data
    all_pairs = load_ground_truth()
    
    if len(all_pairs) > SAMPLE_SIZE:
        test_samples = random.sample(all_pairs, SAMPLE_SIZE)
    else:
        test_samples = all_pairs
        
    print(f"🧪 Benchmarking on {len(test_samples)} random samples...")

    # 2. Load Model
    print("🤖 Loading Model...")
    try:
        model, tokenizer = load(BASE_MODEL, adapter_path=str(ADAPTER_PATH))
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        return

    # 3. Predict & Compare
    correct_count = 0
    errors = []
    
    start_time = time.time()
    
    for retailer, name, true_key in tqdm(test_samples, desc="Predicting"):
        pred_key = ai_predict(model, tokenizer, name)
        
        if pred_key == true_key:
            correct_count += 1
        else:
            errors.append({
                "product": name,
                "truth": true_key,
                "predicted": pred_key,
                "retailer": retailer
            })
            
    total_time = time.time() - start_time
    
    # 4. Report
    accuracy = (correct_count / len(test_samples)) * 100
    
    print("\n" + "="*40)
    print(f"🎯 BENCHMARK RESULTS")
    print("="*40)
    print(f"Accuracy: {accuracy:.2f}% ({correct_count}/{len(test_samples)})")
    print(f"Time Taken: {total_time:.2f}s (Avg: {total_time/len(test_samples):.3f}s/item)")
    print("="*40)
    
    if errors:
        print("\n❌ Incorrect Predictions (Analysis):")
        for i, err in enumerate(errors[:10], 1): # Show top 10 errors
            print(f"{i}. [{err['retailer']}] {err['product']}")
            print(f"   Expected: {err['truth']}")
            print(f"   Got:      {err['predicted']}")
            print("-" * 20)
            
if __name__ == "__main__":
    main()
