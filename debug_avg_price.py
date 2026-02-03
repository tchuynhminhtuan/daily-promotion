
import pandas as pd
import os

# Load data
file_path = "catalog/output/clean_data_2026-02-03.csv"
if not os.path.exists(file_path):
    print(f"File not found: {file_path}")
    exit(1)

df = pd.read_csv(file_path)

# Filter for Apple Watch SE 3 GPS 44mm
# Filter for Apple Watch SE 3 keys
df_key = df[df['product_key'].str.contains('apple_watch_se_3', na=False)]
print("--- Distinct Product Keys Found ---")
print(df_key['product_key'].unique())

print(f"\nFound {len(df_key)} entries for SE 3 family")

# Get In-Stock only? Normalize.py uses `df_in_stock` for avg calculation?
# Line 901: avg_prices = df_in_stock.groupby(['product_key', 'variant_storage'])['price'].mean()
# Line 815: df_in_stock = df[df['stock'] == 'Yes'].copy()

df_in_stock = df_key[df_key['stock'] == 'Yes']
print(f"In-Stock entries: {len(df_in_stock)}")

print("\n--- Contributing Prices ---")
print(df_in_stock[['retailer', 'price', 'variant_color', 'url', 'product_name']])

# Calculate Average
avg_price = df_in_stock['price'].mean()
print(f"\nCalculated Average Price: {avg_price:,.0f} VND")
