
import yaml
import json
import random
from pathlib import Path

# Paths
BASE_DIR = Path(".")
MAPPING_PATH = BASE_DIR / "catalog/retailer_mapping.yaml"
OUTPUT_DIR = BASE_DIR / "experiments/fine_tuning/data"

def main():
    # Load mapping
    print(f"Loading mapping from {MAPPING_PATH}...")
    with open(MAPPING_PATH, 'r', encoding='utf-8') as f:
        mapping = yaml.safe_load(f)

    # Convert to Chat format
    # {"messages": [{"role": "user", "content": "Raw Name"}, {"role": "assistant", "content": "Product Key"}]}
    
    dataset = []
    
    SYSTEM_PROMPT = "You are a product matching assistant. Map the retailer product name to the correct canonical key."
    
    for retailer, products in mapping.items():
        for raw_name, correct_key in products.items():
            entry = {
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Map this product: {raw_name}"},
                    {"role": "assistant", "content": correct_key}
                ]
            }
            dataset.append(entry)

    print(f"Total examples: {len(dataset)}")
    
    # Shuffle and Split
    random.seed(42)
    random.shuffle(dataset)
    
    split_idx = int(len(dataset) * 0.9) # 90% train, 10% validation
    train_data = dataset[:split_idx]
    valid_data = dataset[split_idx:]
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(OUTPUT_DIR / "train.jsonl", 'w', encoding='utf-8') as f:
        for item in train_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            
    with open(OUTPUT_DIR / "valid.jsonl", 'w', encoding='utf-8') as f:
        for item in valid_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            
    print(f"Saved {len(train_data)} training examples to {OUTPUT_DIR / 'train.jsonl'}")
    print(f"Saved {len(valid_data)} validation examples to {OUTPUT_DIR / 'valid.jsonl'}")

if __name__ == "__main__":
    main()
