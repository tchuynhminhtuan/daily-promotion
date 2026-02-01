
import pandas as pd
import yaml
from pathlib import Path

BASE_DIR = Path("/Users/brucehuynh/GitHub/daily-promotion")
OUTPUT_DIR = BASE_DIR / "catalog/output"
MAPPING_PATH = BASE_DIR / "catalog/retailer_mapping.yaml"
SUGGESTIONS_FILE = BASE_DIR / "catalog/new_ai_mappings.yaml"

RETAILER_MAP_REV = {
    'FPT Shop': '1-fpt',
    'Mobile World': '2-mw', 
    'Viettel Store': '3-viettel',
    'HoangHa': '4-hoangha',
    'Di Động Việt': '5-ddv',
    'CellphoneS': '6-cps'
}

def load_mapping():
    with open(MAPPING_PATH, 'r') as f:
        return yaml.safe_load(f)

def main():
    # Find latest clean data
    import glob
    files = sorted(glob.glob(str(OUTPUT_DIR / "clean_data_*.csv")))
    if not files:
        print("No clean data found.")
        return
    
    latest_file = files[-1]
    print(f"Analyzing {latest_file}...")
    
    df = pd.read_csv(latest_file)
    mapping = load_mapping()
    
    new_mappings = {}
    count = 0
    
    for _, row in df.iterrows():
        retailer = row['retailer']
        original = str(row['original_name']).strip()
        key = row['product_key']
        
        # Check if matched manually
        is_manual = False
        if retailer in mapping:
            if original in mapping[retailer]:
                is_manual = True
        
        if not is_manual:
            # It's an AI or Regex match
            # Add to suggestions
            if retailer not in new_mappings:
                new_mappings[retailer] = {}
            
            # Avoid duplicates
            if original not in new_mappings[retailer]:
                new_mappings[retailer][original] = key
                count += 1
    
    # Save to YAML in a format copy-pasteable to retailer_mapping.yaml
    if new_mappings:
        print(f"Found {count} new matches from AI/Regex!")
        with open(SUGGESTIONS_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(new_mappings, f, allow_unicode=True, sort_keys=False)
        print(f"Saved suggestions to {SUGGESTIONS_FILE}")
    else:
        print("No new AI mappings found (everything was already manual?).")

if __name__ == "__main__":
    main()
