#!/usr/bin/env python3
"""
Analyze unmatched products to understand why they don't match
and suggest catalog additions or matching improvements
"""

import pandas as pd
import re
from collections import Counter, defaultdict
from pathlib import Path

# Load unmatched products
unmatched_csv = Path("/Users/brucehuynh/GitHub/daily-promotion/analysis/normalized/unmatched_products_2026-01-31.csv")
df_unmatched = pd.read_csv(unmatched_csv)

print("=== UNMATCHED PRODUCTS ANALYSIS ===\n")
print(f"Total unmatched: {len(df_unmatched)}")
print(f"Unique products: {df_unmatched['original_name'].nunique()}\n")

# Categorize by product type
categories = {
    'AirPods': [],
    'Apple Watch': [],
    'MacBook': [],
    'iPad': [],
    'iPhone': [],
    'Mac mini': [],
    'iMac': [],
    'Other': []
}

for _, row in df_unmatched.iterrows():
    name = row['original_name']
    
    if pd.isna(name) or name.strip() == '':
        categories['Other'].append(row)
        continue
        
    if 'AirPods' in name or 'Tai nghe' in name:
        categories['AirPods'].append(row)
    elif 'Apple Watch' in name:
        categories['Apple Watch'].append(row)
    elif 'MacBook' in name:
        categories['MacBook'].append(row)
    elif 'iPad' in name:
        categories['iPad'].append(row)
    elif 'iPhone' in name:
        categories['iPhone'].append(row)
    elif 'Mac mini' in name:
        categories['Mac mini'].append(row)
    elif 'iMac' in name:
        categories['iMac'].append(row)
    else:
        categories['Other'].append(row)

# Print category summaries
print("\n=== BY CATEGORY ===")
for cat, items in categories.items():
    if items:
        print(f"\n{cat}: {len(items)} unmatched")
        
        # Get unique names
        unique_names = set(item['original_name'] for item in items if pd.notna(item['original_name']))
        
        if len(unique_names) <= 10:
            for name in sorted(unique_names):
                print(f"  - {name}")
        else:
            # Show top 10
            name_counts = Counter(item['original_name'] for item in items)
            print(f"  Top 10 most frequent:")
            for name, count in name_counts.most_common(10):
                print(f"    {count}x: {name}")

# Detailed AirPods analysis
print("\n\n=== AIRPODS DETAILED ANALYSIS ===")
if categories['AirPods']:
    airpods_names = [item['original_name'] for item in categories['AirPods'] if pd.notna(item['original_name'])]
    
    # Extract model patterns
    models = defaultdict(list)
    for name in airpods_names:
        if 'AirPods Pro 3' in name or 'Pro 3' in name:
            models['AirPods Pro 3'].append(name)
        elif 'AirPods Pro 2' in name or 'Pro 2' in name:
            models['AirPods Pro 2'].append(name)
        elif 'AirPods 4' in name and 'chống ồn' in name.lower():
            models['AirPods 4 ANC'].append(name)
        elif 'AirPods 4' in name:
            models['AirPods 4'].append(name)
        else:
            models['Other AirPods'].append(name)
    
    for model, names in sorted(models.items()):
        print(f"\n{model}: {len(names)} variants")
        for name in list(set(names))[:5]:
            print(f"  - {name}")

# Detailed Apple Watch analysis
print("\n\n=== APPLE WATCH DETAILED ANALYSIS ===")
if categories['Apple Watch']:
    watch_names = [item['original_name'] for item in categories['Apple Watch'] if pd.notna(item['original_name'])]
    
    # Extract series patterns
    series_pattern = defaultdict(list)
    for name in watch_names:
        if 'Series 11' in name or 'series-11' in name.lower():
            if 'Titan' in name or 'titan' in name.lower():
                series_pattern['Series 11 Titanium'].append(name)
            else:
                series_pattern['Series 11 Aluminum'].append(name)
        elif 'Series 10' in name or 'series-10' in name.lower():
            if 'Titan' in name or 'titan' in name.lower():
                series_pattern['Series 10 Titanium'].append(name)
            else:
                series_pattern['Series 10 Aluminum'].append(name)
        else:
            series_pattern['Other Series'].append(name)
    
    for series, names in sorted(series_pattern.items()):
        print(f"\n{series}: {len(names)} variants")
        for name in list(set(names))[:5]:
            print(f"  - {name}")

# Generate suggested catalog additions
print("\n\n=== SUGGESTED CATALOG ADDITIONS ===")

print("\n## AirPods (Missing Category):")
print("""
airpods_pro_2:
  name: "AirPods Pro 2"
  category: "Audio"
  keywords: ["AirPods Pro 2", "Pro 2 2023", "USB-C"]
  
airpods_pro_3:
  name: "AirPods Pro 3"
  category: "Audio"
  keywords: ["AirPods Pro 3", "Pro 3 2025"]
  
airpods_4:
  name: "AirPods 4"
  category: "Audio"
  keywords: ["AirPods 4"]
  
airpods_4_anc:
  name: "AirPods 4 ANC"
  category: "Audio"
  keywords: ["AirPods 4", "chống ồn", "ANC"]
""")

print("\n## Apple Watch Series 10/11 Titanium:")
print("""
apple_watch_series_10_titanium:
  name: "Apple Watch Series 10 (Titanium)"
  category: "Watch"
  keywords: ["Series 10", "Titanium", "Titan"]
  sizes: ["42mm", "46mm"]
  
apple_watch_series_11_titanium:
  name: "Apple Watch Series 11 (Titanium)"
  category: "Watch"
  keywords: ["Series 11", "Titanium", "Titan"]
  sizes: ["42mm", "46mm"]
""")

# Generate stock status summary
print("\n\n=== STOCK STATUS OF UNMATCHED ===")
stock_summary = df_unmatched.groupby('stock').agg({
    'original_name': 'count',
    'price': lambda x: (x > 0).sum()
}).rename(columns={'original_name': 'count', 'price': 'with_price'})

print(stock_summary)

print("\n✅ Analysis complete!")
print(f"\nOutput can be used to:")
print("1. Add missing products to product_catalog_golden_v2.yaml")
print("2. Improve matching logic in 10-Normalize_and_Analyze.py")
