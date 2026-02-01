
import re
import os

TARGET_FILE = 'code/generate_report.py'

NEW_NORMALIZER = '''class ProductNormalizer:
    """Enriches product names using Golden Catalog and Specs."""
    
    def __init__(self):
        self.catalog = {}
        # Adjust path if needed, assuming run from project root or code dir
        # We need absolute path or relative to project root
        # In generate_report.py, PROJECT_ROOT is defined.
        # We will assume PROJECT_ROOT is available in runtime, but here we are rewriting source code.
        # We should keep the code compatible.
        pass # Placeholder, the logic is below

    # We will inject the full methods
'''

# We will read the file and replace via regex or line markers
with open(TARGET_FILE, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add import yaml if missing
if 'import yaml' not in content:
    content = content.replace('import html', 'import html\nimport yaml')

# 2. Insert Helpers
HELPERS = '''
# --- Shared Helpers ---
def clean_price(price):
    if pd.isna(price): return None
    if isinstance(price, (int, float)): 
        val = float(price)
    else:
        s = str(price)
        s_clean = re.sub(r'[.,]', '', s) 
        matches = re.findall(r'\\d+', s_clean)
        if not matches: return None
        val = None
        for m in matches:
            v = float(m)
            if v > 100000 and v < 200000000: 
                 val = v
                 break
                 
    if val and 100000 <= val < 200000000:
        return val
    return None

def normalize_text(text):
    text = str(text).lower()
    text = re.sub(r'\\s+', ' ', text).strip()
    return text
    
def normalize_storage(text):
    text = str(text).lower()
    match = re.search(r'(\\d+)\\s*(gb|tb)', text)
    if match:
        val = int(match.group(1))
        unit = match.group(2)
        return f"{val}{unit}"
    return None
'''

if 'def clean_price' not in content:
    # Insert before class ProductNormalizer
    content = content.replace('class ProductNormalizer:', HELPERS + '\n\nclass ProductNormalizer:')

# 3. Replace ProductNormalizer Class Body
# Find start of class
start_marker = 'class ProductNormalizer:'
end_marker = 'class DataLoader:'

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx != -1 and end_idx != -1:
    # We want to replace everything from start_idx to end_idx (exclusive)
    # But keep the markers? No, replace the class definition entirely.
    
    NEW_CLASS_DEF = '''class ProductNormalizer:
    """Enriches product names using Golden Catalog and Specs."""
    
    def __init__(self):
        self.catalog = {}
        catalog_path = os.path.join(PROJECT_ROOT, "product_catalog_golden_v2.yaml")
        if os.path.exists(catalog_path):
            with open(catalog_path, 'r') as f:
                self.catalog = yaml.safe_load(f)
        else:
            print(f"⚠️ Warning: Catalog not found at {catalog_path}")

    def match_product(self, row_name):
        row_name_norm = normalize_text(row_name)
        best_match_key = None
        best_match_len = 0
        
        for key, info in self.catalog.items():
            cat_name = normalize_text(info['name'])
            if cat_name in row_name_norm:
                if len(cat_name) > best_match_len:
                    best_match_len = len(cat_name)
                    best_match_key = key
        return best_match_key

    def enrich_name(self, name, specs):
        if pd.isna(name): return name
        name_str = str(name)
        specs_str = str(specs) if pd.notna(specs) else ""
        
        # 1. Try to match Catalog
        key = self.match_product(name_str)
        if key:
            golden_name = self.catalog[key]['name']
            
            # 2. Extract Storage
            storage = normalize_storage(name_str)
            if not storage:
                storage = normalize_storage(specs_str)
            
            if storage:
                return f"{golden_name} ({storage})"
            return golden_name
            
        # Fallback
        return name_str.strip()

'''
    # We replace the text between start_idx and end_idx
    # But we need to verify what we are replacing.
    old_block = content[start_idx:end_idx]
    # Check if it's already updated?
    if 'match_product' not in old_block:
        content = content[:start_idx] + NEW_CLASS_DEF + content[end_idx:]


# 4. Update DataLoader to use clean_price
# Target: df[col] = pd.to_numeric(df[col], errors='coerce')
# Replace with: df[col] = df[col].apply(clean_price)
if 'pd.to_numeric(df[col], errors=\'coerce\')' in content:
    content = content.replace("df[col] = pd.to_numeric(df[col], errors='coerce')", "df[col] = df[col].apply(clean_price)")
elif 'pd.to_numeric(df[col], errors="coerce")' in content:
    content = content.replace('df[col] = pd.to_numeric(df[col], errors="coerce")', 'df[col] = df[col].apply(clean_price)')

with open(TARGET_FILE, 'w', encoding='utf-8') as f:
    f.write(content)

print("Patch applied successfully.")
