
import sys
import os
import yaml
import re

# Add src/processing to path to import normalize
sys.path.append(os.path.join(os.getcwd(), 'src', 'processing'))

# Mock catalog/mapping load to avoid huge dependencies if possible, 
# but normalize.py imports them. Let's just import match_product from normalize
# Wait, normalize.py is a script, not module. I'll read headers to import properly or just replicate logic?
# normalize.py has `match_product` function.

# Let's import the necessary modules first
from src.processing.normalize import match_product, load_catalog, load_retailer_mapping

# Load real data
print("Loading catalogs...")
catalog = load_catalog()
retailer_mapping = load_retailer_mapping()
print(f"Loaded {len(catalog)} catalog items and {len(retailer_mapping)} rules.")

# Test Case
test_name = "Apple Watch SE 3 GPS + Cellular 44mm viền nhôm dây thể thao"
test_retailer = "Mobile World"
test_specs = "44mm" # From CSV

print(f"\nTesting Mapping for:\nName: {test_name}\nRetailer: {test_retailer}\n")

# Run Match
key = match_product(test_name, test_specs, catalog, test_retailer, retailer_mapping)

print(f"Resulting Key: {key}")

if key:
    print(f"Catalog Name: {catalog[key]['name']}")
else:
    print("NO MATCH FOUND")
