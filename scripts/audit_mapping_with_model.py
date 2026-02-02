
import yaml
import sys
from mlx_lm import load, generate
from tqdm import tqdm

MAPPING_FILE = "catalog/retailer_mapping.yaml"
ADAPTER_PATH = "experiments/fine_tuning/adapters"
BASE_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"

def load_mapping():
    with open(MAPPING_FILE, 'r') as f:
        return yaml.safe_load(f)

def main():
    print("🚀 Loading Retailer Mapping Audit...")
    data = load_mapping()
    
    print(f"🧠 Loading Model: {BASE_MODEL}...")
    model, tokenizer = load(BASE_MODEL, adapter_path=ADAPTER_PATH)
    
    # Flatten list
    items_to_check = []
    for retailer, mappings in data.items():
        if not mappings: continue
        for raw_name, current_key in mappings.items():
            items_to_check.append({
                "retailer": retailer,
                "raw": raw_name,
                "current": current_key
            })
            
    print(f"🔍 Auditing {len(items_to_check)} mappings...")
    
    mismatches = []
    
    # Batch processing or one-by-one? One-by-one for specific logic.
    # We want the model to output the CANONICAL KEY.
    # But the model was trained on Q/A, not "extraction to key".
    # Hmmm. The model knows "iPad Air M3 has M3 chip".
    # It doesn't necessarily know the internal key "ipad_air_11_inch_m3".
    # So we should ask it to "Name the product" or "Identify".
    # Let's ask: "Identify the exact product model name for: {raw}"
    # Then we fuzzy match the name to our keys? 
    # Or maybe we rely on the fact that we fine-tuned it on specs?
    
    # Actually, the user wants to check if the mapping is 'correct'.
    # If I ask "What chip does {raw} have?", and it answers "M3", but the key is "ipad_air_m2", then it's a mismatch.
    # PROMPT STRATEGY:
    # "Analyze the product name '{raw}'. Does it refer to '{current_key}'? Answer YES or NO."
    # But keys are internal (underscores). The model knows "iPad Air 11-inch (M3)".
    # It might confuse "ipad_air_11_inch_m3" (machine key) vs user text.
    
    # Better Strategy:
    # prompt = "Identify the product model, screen size, and chip for: {raw}"
    # output = "iPad Air, 11 inch, M3 chip"
    # We parse this and compare with `current_key` (which implies M3, 11 inch).
    
    # Let's try a simpler one:
    # "State the canonical product name for: {raw}" via 1-shot example?
    # Or just ask it to describe the item.
    
    print("\n--- Start Audit (Top 50 samples for speed) ---")
    
    audit_log = []
    
    for item in tqdm(items_to_check[:50]): # Limit for demo speed
        raw = item['raw']
        current = item['current']
        
        prompt = f"""<|im_start|>system
You are an expert product mapper. Analyze the product listing string.
<|im_end|>
<|im_start|>user
Identify the core product model, chip, and year from this listing: "{raw}"
Format: Model - Chip - Year
<|im_end|>
<|im_start|>assistant
"""
        response = generate(model, tokenizer, prompt=prompt, max_tokens=50, verbose=False).strip()
        
        # Heuristic check
        # If listed as M3 but key says M2 -> Flag
        flagged = False
        if "M3" in raw and "m2" in current: flagged = True
        if "M5" in raw and "m4" in current: flagged = True
        if "S11" in raw and "series_10" in current: flagged = True
        
        # Ai Comparison
        # If response contradicts current key
        
        audit_log.append({
            "retailer": item['retailer'],
            "raw": raw,
            "key": current,
            "ai_analysis": response,
            "flagged": flagged
        })

    # Print Report
    print(f"\n{'Retailer':<15} | {'Raw Name':<40} | {'Key':<20} | {'AI Analysis'}")
    print("-" * 100)
    for log in audit_log:
        if log['flagged'] or "M3" in log['raw'] or "M5" in log['raw']:
             print(f"{log['retailer']:<15} | {log['raw'][:40]:<40} | {log['key'][:20]:<20} | {log['ai_analysis']}")

if __name__ == "__main__":
    main()
