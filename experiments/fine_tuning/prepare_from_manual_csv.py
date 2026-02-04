#!/usr/bin/env python3
"""
Prepare Training Data from Manual-Fixed CSV
============================================
Uses the manually corrected mappings to generate fresh training data for Llama 3B.

Input: experiments/manual-fixed-2026-02-03.csv
Output: experiments/fine_tuning/data/train.jsonl, valid.jsonl
"""

import csv
import json
import random
from pathlib import Path
from collections import defaultdict

# Paths
INPUT_CSV = Path("experiments/manual-fixed-2026-02-03.csv")
OUTPUT_DIR = Path("experiments/fine_tuning/data")
TRAIN_FILE = OUTPUT_DIR / "train.jsonl"
VALID_FILE = OUTPUT_DIR / "valid.jsonl"

SYSTEM_PROMPT = "You are a product matching assistant. Map the retailer product name to the correct canonical key."

def load_manual_data():
    """Load unique (Product_Name, mapped) pairs from the CSV."""
    pairs = []
    seen = set()
    
    with open(INPUT_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            product_name = row.get('Product_Name', '').strip()
            mapped = row.get('mapped', '').strip()
            
            # Clean up mapped (some have newlines from bad editing)
            mapped = mapped.split('\n')[0].strip()
            
            # Skip invalid entries
            if not product_name or not mapped:
                continue
            if len(product_name) < 5:
                continue
                
            # Dedupe
            key = (product_name.lower(), mapped)
            if key in seen:
                continue
            seen.add(key)
            
            pairs.append({
                "input": product_name,
                "output": mapped
            })
    
    return pairs

def augment_data(pairs):
    """
    Augment the dataset by:
    1. Repeating high-quality manual data
    2. Adding minor variations
    """
    augmented = []
    
    # Original data (repeat 3x for emphasis)
    for p in pairs:
        for _ in range(3):
            augmented.append(p.copy())
    
    # Add variations
    prefixes = ["", "Điện thoại ", "Laptop ", "Máy tính bảng ", "Đồng hồ ", "Tai nghe "]
    suffixes = ["", " Chính hãng", " VN/A", " Trả góp 0%"]
    
    for p in pairs:
        # Add 2 random variations per item
        for _ in range(2):
            prefix = random.choice(prefixes)
            suffix = random.choice(suffixes)
            variant = f"{prefix}{p['input']}{suffix}".strip()
            augmented.append({
                "input": variant,
                "output": p["output"]
            })
    
    return augmented

def format_for_chat(pairs):
    """Convert to chat format for fine-tuning."""
    formatted = []
    for p in pairs:
        entry = {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Map this product: {p['input']}"},
                {"role": "assistant", "content": p['output']}
            ]
        }
        formatted.append(entry)
    return formatted

def main():
    print("🚀 Preparing Training Data from Manual-Fixed CSV")
    print(f"📄 Input: {INPUT_CSV}")
    
    # 1. Load manual data
    manual_data = load_manual_data()
    print(f"✅ Loaded {len(manual_data)} unique manual mappings")
    
    # Show distribution
    output_counts = defaultdict(int)
    for p in manual_data:
        output_counts[p['output']] += 1
    print(f"📊 Unique product keys: {len(output_counts)}")
    
    # 2. Augment
    augmented = augment_data(manual_data)
    print(f"✅ Augmented to {len(augmented)} samples")
    
    # 3. Format for chat
    chat_data = format_for_chat(augmented)
    
    # 4. Shuffle and split (95% train, 5% valid)
    random.shuffle(chat_data)
    split_idx = int(len(chat_data) * 0.95)
    train_data = chat_data[:split_idx]
    valid_data = chat_data[split_idx:]
    
    # 5. Save
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(TRAIN_FILE, 'w', encoding='utf-8') as f:
        for item in train_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    with open(VALID_FILE, 'w', encoding='utf-8') as f:
        for item in valid_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    print(f"\n💾 Saved {len(train_data)} training samples to {TRAIN_FILE}")
    print(f"💾 Saved {len(valid_data)} validation samples to {VALID_FILE}")
    print("\n✅ Ready for fine-tuning!")
    print("Run: mlx_lm.lora --model mlx-community/Llama-3.2-3B-Instruct-4bit --data experiments/fine_tuning/data --train --iters 1000 --adapter-path experiments/fine_tuning/adapters_llama")

if __name__ == "__main__":
    main()
