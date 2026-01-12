import os
import glob
import pandas as pd
from datetime import datetime
from sentence_transformers import SentenceTransformer, util
import numpy as np

# --- CONFIG ---
CONTENT_DIR = "content"
OUTPUT_DIR = "analysis_result"
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
SIMILARITY_THRESHOLD = 0.65  # Slightly looser to catch "iPhone 16 Pro Max" vs "DT iPhone 16 Pro Max"
ANCHOR_RETAILER_KEY = "1-fpt" # FPT is our Anchor

def get_latest_date_folder():
    """Finds the latest date folder in content/"""
    dates = []
    if not os.path.exists(CONTENT_DIR):
        print(f"Error: {CONTENT_DIR} not found.")
        return None
        
    for d in os.listdir(CONTENT_DIR):
        try:
            # Check if it looks like a date YYYY-MM-DD
            datetime.strptime(d, "%Y-%m-%d")
            dates.append(d)
        except ValueError:
            continue
            
    if not dates:
        return None
    
    return sorted(dates)[-1]

def load_data(date_folder):
    """Loads all CSVs from the date folder into a dict of DataFrames"""
    path = os.path.join(CONTENT_DIR, date_folder)
    csv_files = glob.glob(os.path.join(path, "*.csv"))
    
    data = {}
    print(f"📂 Loading data from: {path}")
    
    for f in csv_files:
        filename = os.path.basename(f)
        retailer_code = filename.split('-')[1] # e.g. 1-fpt -> fpt, or match strict patterns
        
        # Mapping filename patterns to standardized keys
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
                # Basic cleaning
                if 'Gia_Khuyen_Mai' in df.columns:
                    # Remove non-numeric chars
                    df['Price'] = df['Gia_Khuyen_Mai'].astype(str).str.replace(r'\D', '', regex=True)
                    df['Price'] = pd.to_numeric(df['Price'], errors='coerce')
                
                # Keep critical cols
                cols_to_keep = ['Product_Name', 'Price', 'Color', 'Link', 'Ton_Kho']
                existing_cols = [c for c in cols_to_keep if c in df.columns]
                df = df[existing_cols]
                
                # Add retailer tag
                df['Retailer'] = key
                data[key] = df
                print(f"  ✅ Loaded {key}: {len(df)} rows")
            except Exception as e:
                print(f"  ❌ Error loading {filename}: {e}")
                
    return data

def semantic_match(anchor_df, target_df, model):
    """
    Matches rows in target_df to anchor_df using vector embeddings.
    Returns target_df with a new 'Matched_Anchor_Name' column.
    """
    if target_df is None or target_df.empty:
        return target_df

    # Encode
    anchor_names = anchor_df['Product_Name'].fillna("").tolist()
    target_names = target_df['Product_Name'].fillna("").tolist()
    
    # Check if empty
    if not anchor_names or not target_names:
        return target_df
    
    # Embeddings
    embeddings1 = model.encode(anchor_names, convert_to_tensor=True)
    embeddings2 = model.encode(target_names, convert_to_tensor=True)
    
    # Compute Cosine Similarity
    cosine_scores = util.cos_sim(embeddings2, embeddings1)
    
    # Assign Matches
    matched_anchor_names = []
    matched_scores = []
    
    for i in range(len(target_names)):
        # Find best match for target_i in anchor list
        scores = cosine_scores[i]
        best_score_idx = np.argmax(scores.cpu().numpy())
        best_score = scores[best_score_idx].item()
        
        if best_score >= SIMILARITY_THRESHOLD:
            match_name = anchor_names[best_score_idx]
        else:
            match_name = None # No confident match
            
        matched_anchor_names.append(match_name)
        matched_scores.append(best_score)
        
    target_df['Anchor_Match'] = matched_anchor_names
    target_df['Match_Score'] = matched_scores
    
    return target_df

def main():
    print("🚀 Starting Apple Semantic Price Analysis...")
    
    # 1. Setup
    latest_date = get_latest_date_folder()
    if not latest_date:
        print("❌ No data folders found.")
        return
        
    print(f"📅 Latest Date: {latest_date}")
    data_map = load_data(latest_date)
    
    if "FPT" not in data_map:
        print("❌ Anchor Retailer (FPT) not found in data.")
        return
        
    fpt_df = data_map['FPT']
    print("🧠 Loading AI Model (SentenceTransformer)...")
    model = SentenceTransformer(MODEL_NAME)
    
    # 2. Master Table Init (Just FPT items first)
    # We want a unified view. 
    # Strategy: 
    # Iterate through all other retailers.
    # Match them to FPT.
    # Join onto FPT.
    
    # Prepare Result Table: Master_Name | FPT_Price | MW_Match | MW_Price | ...
    # Simplify: List of dicts
    
    # We need to handle "Colors" too? 
    # Ideally yes, but "Product_Name" usually contains color in FPT? 
    # Let's inspect FPT names: "iPhone 16 Pro Max 256GB - Titan"
    # If FPT separates Color column, we might want to combine them for matching to be precise.
    # Let's combine Name + Color for better matching context if available.
    
    fpt_df['Full_Name'] = fpt_df['Product_Name'].astype(str) + " " + fpt_df['Color'].fillna("").astype(str)
    
    # Base Result: FPT Frame
    # We will rename cols to FPT_xx
    master_df = fpt_df[['Product_Name', 'Color', 'Price', 'Ton_Kho']].copy()
    master_df.columns = ['Anchor_Name', 'Anchor_Color', 'FPT_Price', 'FPT_Stock']
    master_df['Anchor_Full'] = fpt_df['Full_Name']
    
    combined_results = master_df.copy()
    
    competitors = [k for k in data_map.keys() if k != "FPT"]
    
    for comp in competitors:
        print(f"🔍 Matching {comp} to FPT...")
        comp_df = data_map[comp].copy()
        
        # Create Full Name for matching
        comp_df['Full_Name'] = comp_df['Product_Name'].astype(str) + " " + comp_df['Color'].fillna("").astype(str)
        
        # Do Semantic Search against FPT's Full Names
        # We match Comp -> FPT
        # But we want to join Comp ONTO FPT
        
        # So for every row in FPT, find best match in Comp? 
        # OR for every row in Comp, find best match in FPT?
        # Standard approach: Comp -> FPT (normalize Comp rows to FPT IDs)
        
        # Let's match Comp Names TO FPT Names
        # Anchor = FPT Full Names
        # Target = Comp Full Names
        # But wait, earlier semantic_match function expects (Anchor, Target) and returns Target with Match col.
        # Yes, that works. We will get Comp DF with "Anchor_Match" column.
        
        # Override semantic_match locally to use 'Full_Name'
        anchor_names = master_df['Anchor_Full'].tolist()
        target_names = comp_df['Full_Name'].tolist()
        
        embeddings_anchor = model.encode(anchor_names, convert_to_tensor=True)
        embeddings_target = model.encode(target_names, convert_to_tensor=True)
        
        cosine_scores = util.cos_sim(embeddings_anchor, embeddings_target) # Shape: (Num_FPT, Num_Comp)
        
        # For each FPT item, find the best match in Comp
        # maximizing correctness. 
        # Note: Multiple FPT items might match same Comp item? Or vice versa.
        # Let's do: For each FPT item, find highest scoring Comp item.
        
        best_matches = []
        best_scores = []
        best_prices = []
        best_stocks = []
        best_names = []
        
        for i in range(len(anchor_names)):
            scores = cosine_scores[i] # Scores of this FPT item against ALL Comp items
            best_idx = np.argmax(scores.cpu().numpy())
            best_score = scores[best_idx].item()
            
            if best_score >= SIMILARITY_THRESHOLD:
                # Found a match
                match_row = comp_df.iloc[best_idx]
                best_matches.append(match_row['Full_Name'])
                best_scores.append(best_score)
                best_prices.append(match_row['Price'])
                best_stocks.append(match_row['Ton_Kho'])
                best_names.append(match_row['Product_Name'])
            else:
                best_matches.append(None)
                best_scores.append(None)
                best_prices.append(None)
                best_stocks.append(None)
                best_names.append(None)
        
        # Add to combined
        combined_results[f'{comp}_Match'] = best_names
        combined_results[f'{comp}_Price'] = best_prices
        combined_results[f'{comp}_Stock'] = best_stocks
        combined_results[f'{comp}_Score'] = best_scores
        
    # 3. Save
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    out_file = f"{OUTPUT_DIR}/apple_price_comparison_{latest_date}_semantic.csv"
    
    # Reorder for readability
    # Anchor Name | Anchor Color | FPT Price | MW Price | Viettel Price ...
    
    final_cols = ['Anchor_Name', 'Anchor_Color', 'FPT_Price']
    for comp in competitors:
        final_cols.extend([f'{comp}_Price', f'{comp}_Stock'])
        
    # Also keep match info for debugging?
    # Let's dump everything first
    combined_results.to_csv(out_file, index=False)
    print(f"✅ Analysis Complete! Saved to: {out_file}")
    
    # Print Quick Summary
    print("\n--- SAMPLE MATCHES (MW) ---")
    if 'MW_Match' in combined_results.columns:
        print(combined_results[['Anchor_Name', 'MW_Match', 'MW_Score']].head(5))

if __name__ == "__main__":
    main()
