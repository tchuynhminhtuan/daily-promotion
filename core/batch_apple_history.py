import os
import glob
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer, util
from datetime import datetime

# --- CONFIG ---
CONTENT_DIR = "content"
OUTPUT_DIR = "analysis_result"
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
SIMILARITY_THRESHOLD = 0.65

def get_all_dates():
    """Finds all date folders in content/ sorted chronologically."""
    dates = []
    if not os.path.exists(CONTENT_DIR):
        return []
        
    for d in os.listdir(CONTENT_DIR):
        try:
            datetime.strptime(d, "%Y-%m-%d")
            dates.append(d)
        except ValueError:
            continue
            
    return sorted(dates)

def load_data_for_date(date_folder):
    """Loads CSVs for a specific date."""
    path = os.path.join(CONTENT_DIR, date_folder)
    csv_files = glob.glob(os.path.join(path, "*.csv"))
    data = {}
    
    for f in csv_files:
        filename = os.path.basename(f)
        key = None
        if "1-fpt" in filename: key = "FPT"
        elif "2-mw" in filename: key = "MW"
        elif "3-viettel" in filename: key = "Viettel"
        elif "4-hoangha" in filename: key = "HoangHa"
        elif "5-ddv" in filename: key = "DDV"
        elif "6-cps" in filename: key = "CPS"
        
        if key:
            try:
                df = pd.read_csv(f, sep=';', on_bad_lines='skip')
                if 'Gia_Khuyen_Mai' in df.columns:
                    df['Price'] = df['Gia_Khuyen_Mai'].astype(str).str.replace(r'\D', '', regex=True)
                    df['Price'] = pd.to_numeric(df['Price'], errors='coerce')
                
                cols_to_keep = ['Product_Name', 'Price', 'Color', 'Ton_Kho']
                existing_cols = [c for c in cols_to_keep if c in df.columns]
                df = df[existing_cols]
                data[key] = df
            except Exception:
                pass
    return data

def process_date(date, model):
    """
    Processes a single date: Loads data, matches to FPT (Daily Anchor), returns unified DF row.
    """
    data_map = load_data_for_date(date)
    
    if "FPT" not in data_map:
        return None  # Skip days without Anchor
        
    fpt_df = data_map['FPT']
    fpt_df['Full_Name'] = fpt_df['Product_Name'].astype(str) + " " + fpt_df['Color'].fillna("").astype(str)
    
    # Base structure: Date | Anchor_Name | Anchor_Color | FPT_Price | (Competitor_Prices...)
    master_df = fpt_df[['Product_Name', 'Color', 'Price', 'Ton_Kho']].copy()
    master_df.columns = ['Anchor_Name', 'Anchor_Color', 'FPT_Price', 'FPT_Stock']
    master_df['Date'] = date
    master_df['Anchor_Full'] = fpt_df['Full_Name'] # Temp for matching
    
    anchor_names = master_df['Anchor_Full'].tolist()
    if not anchor_names:
        return None

    # Pre-encode Anchor (FPT)
    embeddings_anchor = model.encode(anchor_names, convert_to_tensor=True)
    
    competitors = [k for k in data_map.keys() if k != "FPT"]
    
    for comp in competitors:
        comp_df = data_map[comp].copy()
        if comp_df.empty:
            master_df[f'{comp}_Price'] = None
            master_df[f'{comp}_Stock'] = None
            continue
            
        comp_df['Full_Name'] = comp_df['Product_Name'].astype(str) + " " + comp_df['Color'].fillna("").astype(str)
        target_names = comp_df['Full_Name'].tolist()
        
        embeddings_target = model.encode(target_names, convert_to_tensor=True)
        cosine_scores = util.cos_sim(embeddings_anchor, embeddings_target)
        
        best_prices = []
        best_stocks = []
        
        for i in range(len(anchor_names)):
            scores = cosine_scores[i]
            best_idx = np.argmax(scores.cpu().numpy())
            best_score = scores[best_idx].item()
            
            if best_score >= SIMILARITY_THRESHOLD:
                match_row = comp_df.iloc[best_idx]
                best_prices.append(match_row['Price'])
                best_stocks.append(match_row['Ton_Kho'])
            else:
                best_prices.append(None)
                best_stocks.append(None)
        
        master_df[f'{comp}_Price'] = best_prices
        master_df[f'{comp}_Stock'] = best_stocks
        
    return master_df

def main():
    print("🚀 Starting Batch Apple History Analysis (Time-Travel Mode)...")
    
    # 1. Init
    dates = get_all_dates()
    print(f"📅 Found {len(dates)} days of history ({dates[0]} to {dates[-1]})")
    
    print("🧠 Loading AI Model...")
    model = SentenceTransformer(MODEL_NAME)
    
    all_history = []
    
    # 2. Loop
    print("⏳ Processing... ", end="", flush=True)
    for i, date in enumerate(dates):
        if i % 5 == 0:
            print(f"{date}...", end=" ", flush=True)
            
        daily_df = process_date(date, model)
        if daily_df is not None:
            all_history.append(daily_df)
            
    print("\n✅ Batch Processing Complete.")
    
    # 3. Aggregate
    if not all_history:
        print("❌ No valid history generated.")
        return
        
    final_df = pd.concat(all_history, ignore_index=True)
    
    # 4. Save
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    out_file = f"{OUTPUT_DIR}/apple_price_history_master.csv"
    
    # Cleanup Columns
    if 'Anchor_Full' in final_df.columns:
        final_df = final_df.drop(columns=['Anchor_Full'])
        
    final_df.to_csv(out_file, index=False)
    print(f"💾 Master History Saved to: {out_file}")
    print(f"   Total Rows: {len(final_df)}")

if __name__ == "__main__":
    main()
