#!/usr/bin/env python3
"""
Promo Extraction Experiment
============================
Standalone script to extract structured promotion data from scraped CSVs using Llama 3B.

Usage:
    python experiments/extract_promos_llama.py [--date 2026-02-03] [--limit 50]

Output:
    experiments/extracted_promos_{date}.csv
"""

import os
import sys
import csv
import json
import argparse
from datetime import datetime
from pathlib import Path

# MLX imports
try:
    from mlx_lm import load, generate
except ImportError:
    print("❌ MLX not installed. Run: pip install mlx-lm")
    sys.exit(1)

# Constants
BASE_MODEL = "mlx-community/Llama-3.2-3B-Instruct-4bit"
ADAPTER_PATH = "experiments/fine_tuning/adapters_llama"
DATA_DIR = Path("data/raw")
OUTPUT_DIR = Path("experiments")

# Global model cache
_MODEL = None
_TOKENIZER = None

def load_model():
    """Load Llama 3B with adapters (cached)."""
    global _MODEL, _TOKENIZER
    if _MODEL is None:
        print(f"🤖 Loading Llama 3B from {ADAPTER_PATH}...")
        _MODEL, _TOKENIZER = load(BASE_MODEL, adapter_path=ADAPTER_PATH)
        print("✅ Model loaded!", flush=True)
    return _MODEL, _TOKENIZER

def extract_promo(promo_text: str) -> dict:
    """
    Use Llama 3B to extract structured promo data from raw text.
    
    Returns dict with keys:
    - promo_type: "Discount", "Gift", "Installment", "Trade-in", etc.
    - discount_value: Numeric value if applicable
    - gifts: List of gift items
    - requirements: Conditions (payment method, min purchase, etc.)
    - expiry: Expiry date if mentioned
    """
    if not promo_text or len(promo_text.strip()) < 10:
        return {"promo_type": "None", "raw": promo_text}
    
    model, tokenizer = load_model()
    
    SYSTEM_PROMPT = """Bạn là AI trích xuất thông tin khuyến mãi.
Trả về JSON với các key sau:
- promo_type: Loại KM chính ("Giảm giá", "Tặng quà", "Trả góp 0%", "Thu cũ đổi mới")
- discount_value: Số tiền giảm (số nguyên, không có đơn vị)
- gifts: Danh sách quà tặng (array)
- requirements: Điều kiện áp dụng (array)
- expiry: Ngày hết hạn nếu có

CHỈ trả về JSON, không giải thích."""

    # Truncate if too long
    text = promo_text[:500] if len(promo_text) > 500 else promo_text
    
    prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
{SYSTEM_PROMPT}<|eot_id|>
<|start_header_id|>user<|end_header_id|>
Trích xuất khuyến mãi:
"{text}"<|eot_id|>
<|start_header_id|>assistant<|end_header_id|>
"""
    
    try:
        response = generate(model, tokenizer, prompt=prompt, max_tokens=200, verbose=False)
        response = response.strip()
        
        # Try to parse JSON
        if response.startswith("{"):
            # Find the end of JSON object
            brace_count = 0
            end_idx = 0
            for i, char in enumerate(response):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i + 1
                        break
            
            json_str = response[:end_idx]
            return json.loads(json_str)
        else:
            return {"promo_type": "ParseError", "raw_response": response[:100]}
    except Exception as e:
        return {"promo_type": "Error", "error": str(e)[:50]}

def process_csv(csv_path: Path, limit: int = None) -> list:
    """Process a single CSV file and extract promos."""
    results = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        rows = list(reader)
    
    if limit:
        rows = rows[:limit]
    
    total = len(rows)
    print(f"\n📄 Processing {csv_path.name} ({total} rows)...")
    
    for i, row in enumerate(rows):
        product_name = row.get('Product_Name', '')
        khuyen_mai = row.get('Khuyen_Mai', '')
        thanh_toan = row.get('Thanh_Toan', '')
        
        # Combine promo fields
        combined_promo = f"{khuyen_mai}\n{thanh_toan}".strip()
        
        if combined_promo:
            promo_data = extract_promo(combined_promo)
        else:
            promo_data = {"promo_type": "None"}
        
        # Helper to flatten list items (could be strings or dicts)
        def flatten_list(items):
            if not isinstance(items, list):
                return str(items) if items else ""
            result = []
            for item in items:
                if isinstance(item, dict):
                    result.append(str(item.get('name', item.get('value', str(item)))))
                else:
                    result.append(str(item))
            return ", ".join(result)
        
        results.append({
            "Product_Name": product_name,
            "Retailer": csv_path.name.split('-')[1] if '-' in csv_path.name else "unknown",
            "Original_Promo": combined_promo[:200],  # Truncate for CSV
            "Promo_Type": promo_data.get("promo_type", ""),
            "Discount_Value": promo_data.get("discount_value", ""),
            "Gifts": flatten_list(promo_data.get("gifts", [])),
            "Requirements": flatten_list(promo_data.get("requirements", [])),
            "Expiry": promo_data.get("expiry", "")
        })
        
        # Progress
        if (i + 1) % 10 == 0:
            print(f"   Processed {i+1}/{total}...", flush=True)
    
    return results

def main():
    parser = argparse.ArgumentParser(description="Extract promos from scraped CSVs using Llama 3B")
    parser.add_argument("--date", type=str, default=None, help="Date folder to process (YYYY-MM-DD)")
    parser.add_argument("--limit", type=int, default=50, help="Max rows per CSV (default: 50)")
    parser.add_argument("--file", type=str, default=None, help="Specific CSV file to process")
    args = parser.parse_args()
    
    # Determine date
    if args.date:
        date_str = args.date
    else:
        # Use latest date folder
        date_folders = sorted([d for d in DATA_DIR.iterdir() if d.is_dir()])
        if not date_folders:
            print("❌ No data folders found in data/raw/")
            sys.exit(1)
        date_str = date_folders[-1].name
    
    data_path = DATA_DIR / date_str
    if not data_path.exists():
        print(f"❌ Folder not found: {data_path}")
        sys.exit(1)
    
    print(f"🚀 Promo Extraction Experiment")
    print(f"📅 Date: {date_str}")
    print(f"📁 Source: {data_path}")
    print(f"🔢 Limit: {args.limit} rows/file")
    
    # Find CSVs
    if args.file:
        csv_files = [data_path / args.file]
    else:
        csv_files = sorted(data_path.glob("*.csv"))
    
    if not csv_files:
        print("❌ No CSV files found")
        sys.exit(1)
    
    # Process all CSVs
    all_results = []
    for csv_file in csv_files:
        if csv_file.exists():
            results = process_csv(csv_file, limit=args.limit)
            all_results.extend(results)
    
    # Save output
    output_file = OUTPUT_DIR / f"extracted_promos_{date_str}.csv"
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        if all_results:
            writer = csv.DictWriter(f, fieldnames=all_results[0].keys(), delimiter=';')
            writer.writeheader()
            writer.writerows(all_results)
    
    print(f"\n✅ Done! Extracted {len(all_results)} promos")
    print(f"📄 Output: {output_file}")
    
    # Show sample
    if all_results:
        print("\n📊 Sample results:")
        for r in all_results[:3]:
            print(f"   {r['Product_Name'][:30]}... → {r['Promo_Type']} | {r['Discount_Value']}")

if __name__ == "__main__":
    main()
