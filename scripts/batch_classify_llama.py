
import sys
import os
import glob
import pandas as pd
from pathlib import Path
from tqdm import tqdm

# Setup paths
BASE_DIR = Path(os.getcwd())
sys.path.append(str(BASE_DIR / "src"))

# Import normalize logic
try:
    from processing.normalize import load_catalog, load_retailer_mapping, ai_predict_key, load_ai_model, match_product
except ImportError:
    # Fallback if running from root
    sys.path.append(str(BASE_DIR))
    from src.processing.normalize import load_catalog, load_retailer_mapping, ai_predict_key, load_ai_model, match_product

def classify_all(date_folder):
    # 1. Setup
    print("🚀 Initializing Llama 3B Model...")
    if not load_ai_model():
        print("❌ Failed to load AI model. Exiting.")
        return

    catalog = load_catalog()
    retailer_mapping = load_retailer_mapping()
    
    # 2. Find CSVs
    target_dir = BASE_DIR / "data/raw" / date_folder
    csv_files = glob.glob(str(target_dir / "*.csv"))
    
    if not csv_files:
        print(f"❌ No CSV files found in {target_dir}")
        return

    print(f"📂 Found {len(csv_files)} CSV files. Processing...")
    
    results = []
    
    for file_path in csv_files:
        filename = os.path.basename(file_path)
        retailer = filename.split('-')[1] if '-' in filename else "Unknown"
        
        try:
            # Read CSV with flexible handling
            try:
                df = pd.read_csv(file_path, sep=';', on_bad_lines='skip')
            except:
                try:
                    df = pd.read_csv(file_path, sep=',', on_bad_lines='skip')
                except:
                    print(f"⚠️ Could not read {filename}")
                    continue
            
            # Identify Name Column
            name_cols = [c for c in df.columns if 'name' in c.lower() or 'tên' in c.lower()]
            if not name_cols:
                continue
            name_col = name_cols[0]
            
            # Identify Specs Column (optional)
            specs_col = next((c for c in df.columns if 'specs' in c.lower() or 'thông số' in c.lower()), None)

            print(f"  👉 Processing {filename} ({len(df)} rows)...")

            for _, row in tqdm(df.iterrows(), total=len(df), leave=False):
                raw_name = str(row[name_col]).strip()
                raw_specs = str(row[specs_col]).strip() if specs_col and pd.notna(row[specs_col]) else ""
                
                if len(raw_name) < 3: continue

                # 1. Get Current Rule/Hybrid Key (What the system currently mostly uses)
                # match_product uses Rules -> AI -> Fuzzy. We want to see if Rules exist.
                current_key = match_product(raw_name, raw_specs, catalog, retailer_mapping=retailer_mapping)
                
                # 2. Get Pure AI Prediction from Llama 3B
                ai_key = ai_predict_key(raw_name)
                
                results.append({
                    "Retailer": retailer,
                    "Product_Name": raw_name,
                    "Current Key (Hybrid)": current_key,
                    "Llama 3B Prediction": ai_key,
                    "Match": current_key == ai_key
                })
                
                
        except Exception as e:
            print(f"❌ Error in {filename}: {e}")

        # Save Incremental Results
        output_path = BASE_DIR / f"experiments/llama_3b_evaluation_{date_folder}.csv"
        res_df = pd.DataFrame(results)
        res_df.to_csv(output_path, index=False)
        print(f"💾 Saved {len(res_df)} rows to {output_path}")

    # Final Summary
    print(f"\n✅ Done! Processed {len(res_df)} products.")
    print(f"📊 Results saved to: {output_path}")
    
    # Summary
    match_rate = (res_df['Match'].sum() / len(res_df)) * 100
    print(f"🎯 Agreement Rate (Hybrid vs Llama): {match_rate:.2f}%")
    
    # Show mismatches
    mismatches = res_df[res_df['Match'] == False]
    if not mismatches.empty:
        print("\n👀 Top 5 Examples where Llama 3B disagrees with Rules/Fuzzy:")
        print(mismatches[['Product_Name', 'Current Key (Hybrid)', 'Llama 3B Prediction']].head(5).to_markdown())

if __name__ == "__main__":
    classify_all("2026-02-03")
