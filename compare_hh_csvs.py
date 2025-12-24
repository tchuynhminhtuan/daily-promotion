
import pandas as pd
import os

# Paths
FILE_OLD = "content/2025-12-24/4-hoangha-2025-12-24.csv"
FILE_NEW = "content/2025-12-24/4-hoangha-2025-12-24_v4.csv"

def analyze(path, label):
    print(f"\n--- Analyzing {label} ({path}) ---")
    if not os.path.exists(path):
        print("File not found.")
        return None
        
    try:
        df = pd.read_csv(path, sep=";")
        print(f"Total Rows: {len(df)}")
        print(f"Columns: {list(df.columns)}")
        print(f"Duplicate Rows (based on Link+Color): {df.duplicated(subset=['Link', 'Color']).sum()}")
        
        # Check Price Coverage
        no_price = df[df['Gia_Khuyen_Mai'] == 0]
        print(f"Items with Price = 0: {len(no_price)}")
        
        # Check Promo Content
        empty_promo = df[df['Khuyen_Mai'].isna() | (df['Khuyen_Mai'] == "")]
        print(f"Items with Empty Promo: {len(empty_promo)}")
        
        # Sample
        print("Sample Row:")
        print(df.iloc[0].to_dict())
        
        return df
    except Exception as e:
        print(f"Error: {e}")
        return None

df_old = analyze(FILE_OLD, "OLD (History version)")
df_new = analyze(FILE_NEW, "NEW (Current version)")

if df_old is not None and df_new is not None:
    print("\n--- COMPARISON ---")
    
    # Common Links
    links_old = set(df_old['Link'])
    links_new = set(df_new['Link'])
    
    print(f"Unique Links in OLD: {len(links_old)}")
    print(f"Unique Links in NEW: {len(links_new)}")
    
    missing_in_new = links_old - links_new
    missing_in_old = links_new - links_old
    
    print(f"Links in OLD but missing in NEW: {len(missing_in_new)}")
    print(f"Links in NEW but missing in OLD: {len(missing_in_old)}")
    
    if missing_in_new:
        print(f"Example missing in NEW: {list(missing_in_new)[:3]}")

    print("\n--- PRICE COMPARISON ---")
    # 1. Prepare clean dataframes
    # Drop duplicates in OLD to get unique keys
    df_old_clean = df_old.drop_duplicates(subset=['Product_Name', 'Color']).copy()
    df_new_clean = df_new.drop_duplicates(subset=['Product_Name', 'Color']).copy()
    
    # 2. Merge
    merged = pd.merge(
        df_old_clean[['Product_Name', 'Color', 'Gia_Khuyen_Mai']], 
        df_new_clean[['Product_Name', 'Color', 'Gia_Khuyen_Mai']], 
        on=['Product_Name', 'Color'], 
        how='inner', 
        suffixes=('_OLD', '_NEW')
    )
    
    # 3. Compare
    merged['Diff'] = merged['Gia_Khuyen_Mai_OLD'] != merged['Gia_Khuyen_Mai_NEW']
    mismatches = merged[merged['Diff']]
    
    print(f"Total overlapping variants: {len(merged)}")
    print(f"Price Mismatches: {len(mismatches)}")
    
    if not mismatches.empty:
        print("\nTOP MISMATCHES (Old vs New):")
        for idx, row in mismatches.head(10).iterrows():
            print(f"- {row['Product_Name']} ({row['Color']}): {row['Gia_Khuyen_Mai_OLD']} vs {row['Gia_Khuyen_Mai_NEW']}")
    else:
        print("✅ All prices match perfectly between versions.")

