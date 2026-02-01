
import sys
import os
sys.path.append(os.path.abspath('code'))
from generate_report import DataLoader
import pandas as pd

# Create a dummy DataLoader
loader = DataLoader()

# Load specific recent data
# We'll use the latest date available in the content directory
dates = ["2026-01-31"]
df = loader.load_all_data(dates=dates)

if df.empty:
    print("No data loaded.")
    sys.exit(1)

# Filter for products that might have been enriched
print(f"Total rows: {len(df)}")
print("--- Sample Enriched Names ---")
# Filter for names that were likely touched:
# 1. Contains (...) for storage
# 2. Contains "Viền" or "Cellular" if it wasn't likely there before (hard to check diff without 'before', but we can check if logic ran)
# Let's just print a mix
enriched = df[
    df['Product Name'].str.contains(r'\(\d+[GT]B\)') | 
    (df['Product Name'].str.contains('Watch') & df['Product Name'].str.contains('Viền|Cellular|LTE'))
]

if not enriched.empty:
    print(enriched[['Channel', 'Product Name', 'Tech_Specs']].head(5).to_string())
else:
    print("No names were enriched. Checking rows with Tech Specs...")
    # Debug: Check rows that HAVE specs but were not enriched
    with_specs = df[df['Tech_Specs'].notna() & (df['Tech_Specs'] != "")]
    if not with_specs.empty:
        print("Rows with specs present:")
        print(with_specs[['Channel', 'Product Name', 'Tech_Specs']].head(3).to_string())
    else:
        print("No Tech_Specs found in data.")
