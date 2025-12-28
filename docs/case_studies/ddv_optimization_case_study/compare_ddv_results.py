
import pandas as pd
import sys
import os

# Files
OLD_CSV = 'content/2025-12-23/5-ddv-2025-12-23_old_code.csv'
NEW_CSV = 'content/2025-12-23/5-ddv-2025-12-23.csv'

def clean_price(val):
    try:
        if pd.isna(val): return 0
        return int(str(val).replace('.', '').replace(',', '').replace('₫', '').strip())
    except:
        return 0

def compare_results():
    if not os.path.exists(OLD_CSV) or not os.path.exists(NEW_CSV):
        print(f"Error: One or both files missing.\nOld: {os.path.exists(OLD_CSV)}\nNew: {os.path.exists(NEW_CSV)}")
        return

    print(f"Comparing:")
    print(f"  Old: {OLD_CSV}")
    print(f"  New: {NEW_CSV}")

    try:
        df_old = pd.read_csv(OLD_CSV, sep=';', on_bad_lines='skip')
        df_new = pd.read_csv(NEW_CSV, sep=';', on_bad_lines='skip')
    except Exception as e:
        print(f"Error reading CSVs: {e}")
        return

    print("-" * 30)
    print(f"Total Rows (Old): {len(df_old)}")
    print(f"Total Rows (New): {len(df_new)}")
    
    # 1. Unknown Colors
    old_unknown = df_old[df_old['Color'].astype(str).str.contains('Unknown', case=False, na=False)]
    new_unknown = df_new[df_new['Color'].astype(str).str.contains('Unknown', case=False, na=False)]
    
    print("-" * 30)
    print(f"Rows with 'Unknown' Color (Old): {len(old_unknown)}")
    print(f"Rows with 'Unknown' Color (New): {len(new_unknown)}")
    
    # 2. Zero Prices
    df_old['Price_Clean'] = df_old['Gia_Khuyen_Mai'].apply(clean_price)
    df_new['Price_Clean'] = df_new['Gia_Khuyen_Mai'].apply(clean_price)
    
    old_zeros = df_old[df_old['Price_Clean'] == 0]
    new_zeros = df_new[df_new['Price_Clean'] == 0]
    
    print("-" * 30)
    print(f"Rows with 0 Price (Old): {len(old_zeros)}")
    print(f"Rows with 0 Price (New): {len(new_zeros)}")
    
    # 3. MacBook Coverage
    # Filter for products containing "MacBook" or "Mac"
    old_mac = df_old[df_old['Product_Name'].astype(str).str.contains('Mac', case=False, na=False)]
    new_mac = df_new[df_new['Product_Name'].astype(str).str.contains('Mac', case=False, na=False)]
    
    # Within Macs, check valid prices
    old_mac_valid = old_mac[old_mac['Price_Clean'] > 0]
    new_mac_valid = new_mac[new_mac['Price_Clean'] > 0]
    
    print("-" * 30)
    print(f"Mac Product Rows (Old): {len(old_mac)}")
    print(f"Mac Product Rows (New): {len(new_mac)}")
    print(f"Valid Mac Prices (Old): {len(old_mac_valid)}")
    print(f"Valid Mac Prices (New): {len(new_mac_valid)}")
    
    # 4. Product Diversity (Unique Name + Color combos)
    # create ID col
    df_old['ID'] = df_old['Product_Name'].astype(str) + " - " + df_old['Color'].astype(str)
    df_new['ID'] = df_new['Product_Name'].astype(str) + " - " + df_new['Color'].astype(str)
    
    unique_old = set(df_old['ID'].unique())
    unique_new = set(df_new['ID'].unique())
    
    print("-" * 30)
    print(f"Unique Variants (Old): {len(unique_old)}")
    print(f"Unique Variants (New): {len(unique_new)}")
    
    missing_in_new = unique_old - unique_new
    new_found = unique_new - unique_old
    
    print(f"Lost Variants: {len(missing_in_new)}")
    print(f"Newly Found Variants: {len(new_found)}")
    
    if len(missing_in_new) > 0 and len(missing_in_new) < 20:
        print("Missing variants (Sample):")
        print(list(missing_in_new))

if __name__ == "__main__":
    compare_results()
