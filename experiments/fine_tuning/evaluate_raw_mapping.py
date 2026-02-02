
import pandas as pd
import glob
from pathlib import Path
from mlx_lm import load, generate
import random

def evaluate_on_raw():
    raw_dir = Path("/Users/brucehuynh/GitHub/daily-promotion/data/raw/2026-02-01")
    csv_files = glob.glob(str(raw_dir / "*.csv"))
    
    if not csv_files:
        print("No CSV files found!")
        return

    # Load Model
    adapter_path = "experiments/fine_tuning/adapters"
    base_model = "Qwen/Qwen2.5-0.5B-Instruct"
    print(f"Loading model {base_model}...")
    model, tokenizer = load(base_model, adapter_path=adapter_path)
    
    print("\n=== EVALUATION ON RAW DATA (2026-02-01) ===\n")
    
    for f in csv_files:
        try:
            # Smart load with fallback separators
            df = None
            for sep in [';', ',', '\t']:
                try:
                    df = pd.read_csv(f, sep=sep, on_bad_lines='skip')
                    if len(df.columns) > 1: break
                except: continue
            
            if df is None or len(df) == 0: continue
            
            # Find name column
            name_col = next((c for c in df.columns if c.lower() in ['product_name', 'name', 'tên sản phẩm']), None)
            if not name_col: continue
            
            print(f"📂 Source: {Path(f).name}")
            
            # Sample 3 random products
            samples = df[name_col].dropna().sample(min(3, len(df))).tolist()
            
            for raw_name in samples:
                # Prompt 1: Identification / QA style
                # asking "What is..." to see if it recognizes the entity
                prompt = f"<|im_start|>system\nYou are an expert Apple technical assistant.<|im_end|>\n<|im_start|>user\nDescribe the specifications of: {raw_name}<|im_end|>\n<|im_start|>assistant\n"
                
                response = generate(model, tokenizer, prompt=prompt, max_tokens=100, verbose=False)
                
                print(f"Input:  {raw_name}")
                print(f"Output: {response.strip().replace(chr(10), ' ')}") # Flatten output
                print("-" * 30)
                
        except Exception as e:
            print(f"Error processing {f}: {e}")

if __name__ == "__main__":
    evaluate_on_raw()
