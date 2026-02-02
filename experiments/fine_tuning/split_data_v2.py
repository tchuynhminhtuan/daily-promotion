
import json
import random
from pathlib import Path

BASE_DIR = Path("/Users/brucehuynh/GitHub/daily-promotion/experiments/fine_tuning/data")
INPUT_FILE = BASE_DIR / "training_data_v2.jsonl"
TRAIN_FILE = BASE_DIR / "train.jsonl"
VALID_FILE = BASE_DIR / "valid.jsonl"

def split_data():
    if not INPUT_FILE.exists():
        print(f"Error: {INPUT_FILE} not found")
        return

    print("Reading data...")
    with open(INPUT_FILE, 'r') as f:
        lines = [l.strip() for l in f if l.strip()]

    random.shuffle(lines)
    
    total = len(lines)
    split_idx = int(total * 0.9)
    
    train_data = lines[:split_idx]
    valid_data = lines[split_idx:]
    
    print(f"Total: {total}")
    print(f"Train: {len(train_data)}")
    print(f"Valid: {len(valid_data)}")
    
    with open(TRAIN_FILE, 'w') as f:
        f.write('\n'.join(train_data))
        
    with open(VALID_FILE, 'w') as f:
        f.write('\n'.join(valid_data))
        
    print("Done!")

if __name__ == "__main__":
    split_data()
