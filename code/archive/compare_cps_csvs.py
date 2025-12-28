import pandas as pd
import sys

def compare_csvs(file1, file2):
    print(f"Comparing:")
    print(f"  Old (Historic): {file1}")
    print(f"  New (Current):  {file2}")
    
    try:
        df1 = pd.read_csv(file1, sep=';')
        df2 = pd.read_csv(file2, sep=';')
    except Exception as e:
        print(f"Error reading CSVs: {e}")
        return

    # Normalize columns
    # New CSV might not have Voucher_Image
    cols_to_compare = ['Product_Name', 'Color', 'Ton_Kho', 'Gia_Khuyen_Mai', 'Link']
    
    print(f"\nRow Counts:")
    print(f"  Old: {len(df1)}")
    print(f"  New: {len(df2)}")
    
    # Create composite key for comparison
    df1['Key'] = df1['Product_Name'].astype(str).str.strip() + " | " + df1['Color'].astype(str).str.strip()
    df2['Key'] = df2['Product_Name'].astype(str).str.strip() + " | " + df2['Color'].astype(str).str.strip()
    
    # Find unique keys
    keys1 = set(df1['Key'])
    keys2 = set(df2['Key'])
    
    only_in_1 = keys1 - keys2
    only_in_2 = keys2 - keys1
    common_keys = keys1 & keys2
    
    if only_in_1:
        print(f"\n[MISSING IN NEW] ({len(only_in_1)}) items (present in Old, missing in New):")
        for k in list(only_in_1)[:10]:
            print(f"  - {k}")
        if len(only_in_1) > 10: print("  ... and more")

    if only_in_2:
        print(f"\n[NEW IN NEW] ({len(only_in_2)}) items (missing in Old, present in New):")
        for k in list(only_in_2)[:10]:
            print(f"  - {k}")
        if len(only_in_2) > 10: print("  ... and more")
        
    print(f"\nComparing Common Items ({len(common_keys)}):")
    
    diff_price = []
    diff_stock = []
    
    for key in common_keys:
        row1 = df1[df1['Key'] == key].iloc[0]
        row2 = df2[df2['Key'] == key].iloc[0]
        
        # Compare Price
        p1 = row1.get('Gia_Khuyen_Mai', 0)
        p2 = row2.get('Gia_Khuyen_Mai', 0)
        
        # Clean price
        try:
            p1_val = float(str(p1).replace('.', '').replace(',', '').replace('₫', '').strip() or 0)
        except: p1_val = 0
        try:
            p2_val = float(str(p2).replace('.', '').replace(',', '').replace('₫', '').strip() or 0)
        except: p2_val = 0
        
        if p1_val != p2_val:
            diff_price.append({
                "Key": key,
                "Old_Price": p1_val,
                "New_Price": p2_val,
                "Diff": p2_val - p1_val
            })
            
        # Compare Stock
        s1 = str(row1.get('Ton_Kho', '')).strip().lower()
        s2 = str(row2.get('Ton_Kho', '')).strip().lower()
        
        # Normalize stock values (Yes/No vs others?)
        # CPS usually uses 'Yes' / 'No' or 'In Stock'
        if s1 != s2:
            diff_stock.append({
                "Key": key,
                "Old_Stock": row1.get('Ton_Kho'),
                "New_Stock": row2.get('Ton_Kho')
            })

    if diff_price:
        print(f"\n[PRICE DIFFERENCES] ({len(diff_price)}):")
        for d in diff_price[:20]:
            print(f"  {d['Key']}: {d['Old_Price']} -> {d['New_Price']} (Diff: {d['Diff']})")
        if len(diff_price) > 20: print("  ... and more")
    
    if diff_stock:
        print(f"\n[STOCK DIFFERENCES] ({len(diff_stock)}):")
        for d in diff_stock[:20]:
            print(f"  {d['Key']}: {d['Old_Stock']} -> {d['New_Stock']}")
        if len(diff_stock) > 20: print("  ... and more")

    if not diff_price and not diff_stock and not only_in_1 and not only_in_2:
        print("\n✅ NO DIFFERENCES FOUND. The files are identical in key metrics.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python compare_cps_csvs.py <old_csv> <new_csv>")
    else:
        compare_csvs(sys.argv[1], sys.argv[2])
