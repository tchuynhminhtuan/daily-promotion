
import pandas as pd
import glob
import os

def load_csv(filepath):
    try:
        df = pd.read_csv(filepath, sep=";", on_bad_lines='skip')
        return df
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return pd.DataFrame()

def analyze_df(df, name):
    print(f"--- Analysis for {name} ---")
    print(f"Total Rows: {len(df)}")
    
    if len(df) == 0: return

    # Check for Unknown/Default colors
    unknown_colors = df[df['Color'].astype(str).str.contains('Unknown|Default', case=False, na=False)]
    print(f"Rows with 'Unknown/Default' Color: {len(unknown_colors)}")
    
    # Check for 0 prices
    zero_prices = df[df['Gia_Khuyen_Mai'] == 0]
    print(f"Rows with 0 Price: {len(zero_prices)}")
    
    # Check for Unique Variants (Name + Color)
    # Note: CPS logic splits by storage URL now.
    # We can try to count unique (Product_Name, Color) tuples
    unique_variants = df.drop_duplicates(subset=['Product_Name', 'Color'])
    print(f"Unique Variants (Name + Color): {len(unique_variants)}")
    
    # Sample some colors
    print(f"Sample Colors: {df['Color'].dropna().unique()[:5]}")
    print("\n")

def main():
    # 1. Find Old File
    old_files = glob.glob("content/2025-12-23/6-cps-2025-12-23_old_code.csv")
    if not old_files:
        old_files = glob.glob("content/2025-12-23/6-cps-2025-12-23.csv")
    
    if not old_files:
        print("No old file found in content/2025-12-23/")
        return

    old_file = old_files[0]
    
    # 2. Find New File (Today)
    # Assuming today is 2025-12-24
    new_files = glob.glob("content/2025-12-24/6-cps-*.csv")
    if not new_files:
        print("No new file found in content/2025-12-24/")
        return
        
    new_file = new_files[0] # Pick first one
    
    print(f"Comparing:\n  Old: {old_file}\n  New: {new_file}\n")
    
    df_old = load_csv(old_file)
    df_new = load_csv(new_file)
    
    analyze_df(df_old, "Old Data")
    analyze_df(df_new, "New Data")
    
    # specific check for storage variants
    # If optimization worked, we expect MORE rows or MORE unique Links 
    # (since we now navigate to separate storage URLs)
    
    print("--- Detailed Comparison ---")
    print(f"Old Unique Links: {df_old['Link'].nunique() if 'Link' in df_old.columns else 0}")
    print(f"New Unique Links: {df_new['Link'].nunique() if 'Link' in df_new.columns else 0}")

if __name__ == "__main__":
    main()
