import pandas as pd

pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

# Load datasets
input_new = 'content/2025-12-23/2-mw-2025-12-23.csv'
input_old = 'content/2025-12-23/2-mw-2025-12-23_v1.csv'

df_new = pd.read_csv(input_new, sep=';')
df_old = pd.read_csv(input_old, sep=';')

# Filter for a common high-volume product to analyze differences
target_name = "iPhone 15 128GB" 

print(f"--- Analyzing '{target_name}' ---")

# Filter
subset_new = df_new[df_new['Product_Name'].str.contains(target_name, na=False)]
subset_old = df_old[df_old['Product_Name'].str.contains(target_name, na=False)]

print(f"\n[NEW] Records found: {len(subset_new)}")
print(subset_new[['Product_Name', 'Color', 'Gia_Khuyen_Mai']].sort_values('Color'))

print(f"\n[OLD] Records found: {len(subset_old)}")
print(subset_old[['Product_Name', 'Color', 'Gia_Khuyen_Mai']].sort_values('Color'))

# Check for duplicates in OLD
print("\n[OLD] Duplicates Check (Name + Color):")
dupes = subset_old[subset_old.duplicated(subset=['Product_Name', 'Color'], keep=False)]
if not dupes.empty:
    print(dupes[['Product_Name', 'Color', 'Link']])
else:
    print("No duplicates found in Old.")

print("\n[NEW] Duplicates Check (Name + Color):")
dupes_new = subset_new[subset_new.duplicated(subset=['Product_Name', 'Color'], keep=False)]
if not dupes_new.empty:
    print(dupes_new[['Product_Name', 'Color', 'Link']])
else:
    print("No duplicates found in New.")
