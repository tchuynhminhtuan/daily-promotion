import pandas as pd
import sys

# Load CSVs
try:
    df_new = pd.read_csv('content/2025-12-23/2-mw-2025-12-23.csv', sep=';')
    df_old = pd.read_csv('content/2025-12-23/2-mw-2025-12-23_v1.csv', sep=';')
except Exception as e:
    print(f"Error loading CSVs: {e}")
    sys.exit(1)

# Group by Link (since Link is the input unit)
new_counts = df_new['Link'].value_counts()
old_counts = df_old['Link'].value_counts()

# Merge
df_counts = pd.DataFrame({'New_Count': new_counts, 'Old_Count': old_counts}).fillna(0)
df_counts['Diff'] = df_counts['New_Count'] - df_counts['Old_Count']

# Filter only differences
diffs = df_counts[df_counts['Diff'] != 0].sort_values('Diff')

print("Top Discrepancies (New < Old):")
print(diffs.head(20))

print("\nTop Discrepancies (New > Old):")
print(diffs.tail(20))

# Also check total URLs
print(f"\nTotal URLs in New: {len(new_counts)}")
print(f"Total URLs in Old: {len(old_counts)}")

# Check if any URL is completely missing in New
missing_urls = set(old_counts.index) - set(new_counts.index)
print(f"\nURLs completely missing in New: {len(missing_urls)}")
for url in missing_urls:
    print(url)
