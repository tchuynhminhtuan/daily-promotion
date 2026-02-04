
import pandas as pd
import glob
import os
import sys
from pathlib import Path
from tqdm import tqdm
import time

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

try:
    from mlx_lm import load, generate
except ImportError:
    print("❌ mlx_lm not installed. Use 'pip install mlx-lm'")
    sys.exit(1)

from src.matching.engine import match_product
from src.utils.config import load_catalog

DATA_DIR = PROJECT_ROOT / "data/raw/2026-02-04"
ADAPTER_PATH = PROJECT_ROOT / "experiments/fine_tuning/adapters_llama"
BASE_MODEL = "mlx-community/Llama-3.2-3B-Instruct-4bit"
OUTPUT_CSV = PROJECT_ROOT / "experiments/benchmark_results_full.csv"

def get_raw_products():
    csv_files = glob.glob(str(DATA_DIR / "*.csv"))
    products = []
    
    print(f"📂 Found {len(csv_files)} files in {DATA_DIR}")
    
    for f in csv_files:
        try:
            # Try sniffing or default to common delimiters
            # Fallback to python engine for more leniency
            try:
                df = pd.read_csv(f, sep=None, engine='python', on_bad_lines='skip')
            except:
                # Fallback to simple comma or semicolon
                try:
                    df = pd.read_csv(f, sep=',')
                except:
                    df = pd.read_csv(f, sep=';')

            # Identify name column
            cols = [str(c).lower().strip() for c in df.columns]
            name_col = None
            
            # Map common internal names
            if 'product name' in cols: name_col = df.columns[cols.index('product name')]
            elif 'ten_san_pham' in cols: name_col = df.columns[cols.index('ten_san_pham')]
            elif 'product_name' in cols: name_col = df.columns[cols.index('product_name')]
            elif 'name' in cols: name_col = df.columns[cols.index('name')]
            elif '_raw_name' in cols: name_col = df.columns[cols.index('_raw_name')]
            
            if name_col:
                items = df[name_col].astype(str).dropna().unique().tolist()
                products.extend(items)
            else:
                print(f"⚠️ No name column found in {Path(f).name}. Cols: {cols}")
        except Exception as e:
            print(f"Error reading {f}: {e}")
            
    return sorted(list(set(products)))

def main():
    # 1. Load Data
    raw_names = get_raw_products()
    print(f"📊 Unique Products to Test: {len(raw_names)}")
    
    # Limit for quick testing? User said "ALL".
    # raw_names = raw_names[:20] 
    
    # 2. Load Resources
    print("🧠 Loading Catalog & Rule Engine...")
    catalog = load_catalog()
    
    print(f"🤖 Loading Llama Model ({BASE_MODEL})...")
    model, tokenizer = load(BASE_MODEL, adapter_path=str(ADAPTER_PATH))
    
    SYSTEM_PROMPT = "You are a product matching assistant. Map the retailer product name to the correct canonical key."
    
    results = []
    
    print("🚀 Starting Benchmark...")
    start_time = time.time()
    
    for raw in tqdm(raw_names):
        # A. Rule Based
        rule_key, _ = match_product(raw, "", catalog)
        if rule_key is None:
            rule_key = "Unmatched"
            
        # B. Llama Inference
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Map this product: {raw}"}
        ]
        prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        # Limit tokens to avoid long hallucinations
        response = generate(model, tokenizer, prompt=prompt, max_tokens=20, verbose=False)
        ai_key = response.strip()
        
        # Cleanup AI output (sometimes it outputs extra text?)
        # With current fine-tuning it should be concise.
        
        results.append({
            "Raw Name": raw,
            "Rule Key": rule_key,
            "AI Key": ai_key,
            "Match": rule_key == ai_key
        })
        
    duration = time.time() - start_time
    print(f"✅ Finished in {duration:.2f}s ({duration/len(raw_names):.3f}s/item)")
    
    # 3. Save Results
    df_res = pd.DataFrame(results)
    df_res.to_csv(OUTPUT_CSV, index=False)
    print(f"💾 Results saved to {OUTPUT_CSV}")
    
    # 4. Summary Stats
    agreement = df_res['Match'].mean() * 100
    print(f"\n📊 Agreement Rate (Rule vs AI): {agreement:.2f}%")
    
    # Identify cases where Rule Failed but AI predicted something (Potential Win for AI)
    ai_wins = df_res[(df_res['Rule Key'] == "Unmatched") & (df_res['AI Key'] != "Unmatched")]
    print(f"💡 Potential AI Wins (Rule Failed, AI Predicted): {len(ai_wins)}")
    if not ai_wins.empty:
        print(ai_wins[['Raw Name', 'AI Key']].head(10))
        
    # Identify Conflicts
    conflicts = df_res[(df_res['Rule Key'] != "Unmatched") & (df_res['Rule Key'] != df_res['AI Key'])]
    print(f"\n⚠️ Conflicts (Rule says X, AI says Y): {len(conflicts)}")
    if not conflicts.empty:
        print(conflicts[['Raw Name', 'Rule Key', 'AI Key']].head(10))

if __name__ == "__main__":
    main()
