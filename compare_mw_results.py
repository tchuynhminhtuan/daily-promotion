import pandas as pd

try:
    df_old = pd.read_csv("content/2025-12-23/2-mw-2025-12-23_v1.csv", sep=";")
    df_new = pd.read_csv("content/2025-12-23/2-mw-2025-12-23.csv", sep=";")
except:
    # Try different reading method if delimiter fails
    df_old = pd.read_csv("content/2025-12-23/2-mw-2025-12-23_v1.csv", sep=None, engine='python')
    df_new = pd.read_csv("content/2025-12-23/2-mw-2025-12-23.csv", sep=None, engine='python')

print(f"Old Rows: {len(df_old)}")
print(f"New Rows: {len(df_new)}")

# Normalize Columns
df_old['Product_Name'] = df_old['Product_Name'].str.strip()
df_old['Color'] = df_old['Color'].str.strip()

df_new['Product_Name'] = df_new['Product_Name'].str.strip()
df_new['Color'] = df_new['Color'].str.strip()

# Create Keys
df_old['Key'] = df_old['Product_Name'] + "|" + df_old['Color']
df_new['Key'] = df_new['Product_Name'] + "|" + df_new['Color']

# Find Missing Checks
old_keys = set(df_old['Key'])
new_keys = set(df_new['Key'])

missing_in_new = old_keys - new_keys
print(f"Missing Combinations in New: {len(missing_in_new)}")

if len(missing_in_new) > 0:
    print("\n--- Top 20 Missing Items ---")
    for k in list(missing_in_new)[:20]:
        print(k)

    # Analyze Patterns
    df_missing = df_old[df_old['Key'].isin(missing_in_new)]
    print("\n--- Missing by Product Name (Top 5) ---")
    print(df_missing['Product_Name'].value_counts().head(5))

    print("\n--- Missing by Color (Top 5) ---")
    print(df_missing['Color'].value_counts().head(5))

# Check for Price 0 in NEW
print("\n--- Price 0 Analysis (New File) ---")
df_new['Gia_Khuyen_Mai'] = pd.to_numeric(df_new['Gia_Khuyen_Mai'], errors='coerce').fillna(0)
price_zeros = df_new[df_new['Gia_Khuyen_Mai'] == 0]
print(f"Rows with Price 0: {len(price_zeros)}")
if len(price_zeros) > 0:
    print(price_zeros[['Product_Name', 'Color', 'Link']].head(5))
