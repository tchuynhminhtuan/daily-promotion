import pandas as pd
import sys

# Check if the file exists
FILE = "content/2025-12-28/1-fpt-2025-12-28.csv"

try:
    # Load with correct delimiter
    df = pd.read_csv(FILE, sep=";", encoding="utf-8", on_bad_lines='skip', engine='python')
    
    # Filter for "Unknown" color
    unknowns = df[df["Color"].astype(str).str.contains("Unknown", case=False, na=False)]
    
    print(f"Total Rows: {len(df)}")
    print(f"Unknown Color Rows: {len(unknowns)}")
    
    if len(unknowns) > 0:
        print("\n--- Inspecting Links for Unknown Rows ---")
        for index, row in unknowns.iterrows():
            print(f"Product: {row['Product_Name']}")
            print(f"Link: '{row['Link']}'")
            print("-" * 30)
            
            # Save URLs to file for re-running if valid
            if pd.notna(row['Link']) and str(row['Link']).strip() != "":
                with open("valid_failing_urls.txt", "a") as f:
                    f.write(str(row['Link']).strip() + "\n")
                    
except Exception as e:
    print(f"Error loading CSV: {e}")
