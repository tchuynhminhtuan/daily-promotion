
import yaml
import copy

INPUT_FILE = "product_catalog_golden_v2.yaml"
OUTPUT_FILE = "product_catalog_golden_v2.yaml"

def clean_colors(colors):
    if not colors: return []
    cleaned = []
    for c in colors:
        c_str = str(c).strip()
        if c_str in ['GPS', 'GPS + Cellular', '—', 'Cellular', 'LTE']:
            continue
        cleaned.append(c_str)
    return sorted(list(set(cleaned))) # Dedupe and sort

def fix_catalog():
    with open(INPUT_FILE, 'r') as f:
        catalog = yaml.safe_load(f)

    new_catalog = {}
    
    # Define granular Apple Watch Definitions to OVERWRITE existing ones
    watch_definitions = {
        # --- SERIES 11 ---
        'apple_watch_series_11_aluminum': {
            'name': 'Apple Watch Series 11 (Nhôm)',
            'category': 'Watch',
            'colors': ['Nhôm Bạc', 'Nhôm Vàng Hồng', 'Nhôm Xám Không Gian', 'Nhôm Ánh Sao'],
            'sizes': ['42mm', '46mm'],
            'connectivity': ['GPS', 'GPS + Cellular'],
            'source': 'manual_fix'
        },
        'apple_watch_series_11_titanium': {
            'name': 'Apple Watch Series 11 (Titanium)',
            'category': 'Watch',
            'colors': ['Titan Gold', 'Titan Tự Nhiên', 'Titan Xám'],
            'sizes': ['42mm', '46mm'],
            'connectivity': ['GPS + Cellular'],
            'source': 'manual_fix'
        },
        # --- SERIES 10 ---
        'apple_watch_series_10_aluminum': {
            'name': 'Apple Watch Series 10 (Nhôm)',
            'category': 'Watch',
            'colors': ['Nhôm Đen Bóng', 'Nhôm Vàng Hồng', 'Nhôm Bạc'],
            'sizes': ['42mm', '46mm'],
            'connectivity': ['GPS', 'GPS + Cellular'],
            'source': 'manual_fix'
        },
        'apple_watch_series_10_titanium': {
            'name': 'Apple Watch Series 10 (Titanium)',
            'category': 'Watch',
            'colors': ['Titan Gold', 'Titan Tự Nhiên', 'Titan Xám'],
            'sizes': ['42mm', '46mm'],
            'connectivity': ['GPS + Cellular'],
            'source': 'manual_fix'
        },
        # --- ULTRA ---
        'apple_watch_ultra_2': {
            'name': 'Apple Watch Ultra 2',
            'category': 'Watch',
            'colors': ['Titan Tự Nhiên', 'Titan Đen'],
            'sizes': ['49mm'],
            'connectivity': ['GPS + Cellular'],
            'source': 'manual_fix'
        },
        'apple_watch_ultra_3': {
             'name': 'Apple Watch Ultra 3',
             'category': 'Watch',
             'colors': ['Titan Tự Nhiên', 'Titan Đen'],
             'sizes': ['49mm'],
             'connectivity': ['GPS + Cellular'],
             'source': 'manual_fix'
        },
        # --- SE ---
        'apple_watch_se_2': {
            'name': 'Apple Watch SE 2',
            'category': 'Watch',
            'colors': ['Đen Xanh', 'Trắng Starlight', 'Bạc'],
            'sizes': ['40mm', '44mm'],
            'connectivity': ['GPS', 'GPS + Cellular'],
            'source': 'manual_fix'
        }
    }

    # Keys to REMOVE if found (because we replaced them with granular ones)
    keys_to_remove = [
        'apple_watch_series_11', 'apple_watch_series_11_lte', 
        'apple_watch_series_10', 'apple_watch_series_10_lte',
        'apple_watch_ultra' # Old generic
    ]

    for key, data in catalog.items():
        # Skip if in removal list
        if key in keys_to_remove:
            continue
            
        # Clean Colors for ALL products
        if 'colors' in data:
            data['colors'] = clean_colors(data['colors'])
            
        # Add to new catalog
        new_catalog[key] = data

    # Update with granular watch definitions
    # Note: 'apple_watch_ultra_2' might have been in catalog, we overwrite it with 'update'
    new_catalog.update(watch_definitions)

    # Save
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        yaml.dump(new_catalog, f, allow_unicode=True, sort_keys=False)
    
    print("Catalog fixed and saved.")

if __name__ == "__main__":
    fix_catalog()
