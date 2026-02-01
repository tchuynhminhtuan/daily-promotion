#!/usr/bin/env python3
"""
Validate retailer_mapping.yaml using AI (Ollama - Qwen/Llama)
Processes in small batches to avoid RAM issues.
"""

import yaml
import json
import subprocess
import time
import re
from pathlib import Path

# Configuration
MODEL = "llama3.1:latest"  # Using llama3.1 (can switch to qwen2.5:7b if available)
BATCH_SIZE = 10  # Small batch to avoid RAM issues
DELAY_BETWEEN_BATCHES = 2  # Seconds

BASE_DIR = Path("/Users/brucehuynh/GitHub/daily-promotion")
MAPPING_PATH = BASE_DIR / "catalog/retailer_mapping.yaml"
CATALOG_PATH = BASE_DIR / "catalog/product_catalog.yaml"
OUTPUT_PATH = BASE_DIR / "catalog/validation_results.json"


def load_yaml(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def call_ollama(prompt, model=MODEL):
    """Call Ollama API with a prompt"""
    try:
        result = subprocess.run(
            ["ollama", "run", model, prompt],
            capture_output=True,
            text=True,
            timeout=300
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    except Exception as e:
        return f"ERROR: {e}"


def validate_batch(batch, catalog, model=MODEL):
    """
    Validate a batch of retailer_name -> product_key mappings
    Returns list of validation results
    """
    results = []
    
    # Build prompt for batch validation with comprehensive context
    prompt = """You are an expert validator for Apple product name mappings in Vietnam retail market.

=== IMPORTANT CONTEXT ===

1. CONNECTIVITY RULES (Apple Watch):
   - "5G", "LTE", "Cellular", "4G" → product key should end with "_lte"
   - "GPS" only (no cellular) → product key should end with "_gps"
   - Example: "Apple Watch SE 3 40mm (5G)" → "apple_watch_se_3_lte" (CORRECT)
   - Example: "Apple Watch SE 3 40mm (GPS)" → "apple_watch_se_3_gps" (CORRECT)

2. SIZE is an ATTRIBUTE, not part of product key:
   - Watch sizes (40mm, 42mm, 44mm, 46mm, 49mm) are handled separately
   - "Apple Watch Series 11 42mm" → "apple_watch_series_11_aluminum" is CORRECT
   - Do NOT suggest adding size to the key

3. STORAGE is an ATTRIBUTE, not part of product key:
   - Storage variants (128GB, 256GB, 512GB, 1TB) are handled separately
   - "iPhone 16 256GB" → "iphone_16" is CORRECT
   - "iPhone 16 Pro 1TB" → "iphone_16_pro" is CORRECT
   - Do NOT mark as incorrect just because storage is different

4. BAND TYPE is an ATTRIBUTE:
   - "Dây Cao Su", "Dây Alpine", "Dây Ocean", "Sport Loop" etc. are attributes
   - Do NOT mark as incorrect for band differences

5. MODEL YEAR:
   - "2024", "2025" in name doesn't change the product key
   - Focus on the model name (SE 3, Series 11, Ultra 3, etc.)

6. VIETNAMESE NAMING:
   - "Viền Nhôm" = Aluminum case
   - "Viền Titan" = Titanium case
   - "Chính Hãng" = Official/Authentic (ignore this)

=== CATALOG PRODUCTS ===
"""
    # Add relevant catalog entries
    relevant_keys = set(item['key'] for item in batch)
    for key in relevant_keys:
        if key in catalog:
            info = catalog[key]
            prompt += f"- {key}: {info.get('name', key)} (Category: {info.get('category', 'Unknown')})\n"
    
    # Add related keys that might be alternatives
    prompt += "\nRelated keys available in catalog:\n"
    for key in catalog.keys():
        if any(k in key for k in ['watch', 'iphone', 'ipad', 'mac']):
            if '_lte' in key or '_gps' in key:
                prompt += f"- {key}\n"
    
    prompt += "\n=== MAPPINGS TO VALIDATE ===\n"
    for i, item in enumerate(batch, 1):
        prompt += f"{i}. \"{item['retailer_name']}\" → \"{item['key']}\"\n"
    
    prompt += """
=== VALIDATION CRITERIA ===
- Mark as CORRECT if the product model matches, even if size/storage/band differs
- Mark as INCORRECT only if:
  a) Wrong product model (e.g., iPhone 15 mapped to iphone_16)
  b) Wrong connectivity (e.g., 5G product mapped to _gps key)
  c) Wrong material (e.g., Titanium Watch mapped to _aluminum key)

Respond with ONLY a JSON array:
[
  {"index": 1, "correct": true, "confidence": 0.95, "reason": "model matches, size is attribute"},
  {"index": 2, "correct": false, "confidence": 0.9, "suggested_key": "apple_watch_se_3_lte", "reason": "5G requires _lte key"}
]
"""
    
    response = call_ollama(prompt, model)
    
    # Parse response
    try:
        # Clean up response to handle DeepSeek/Chain-of-thought and Markdown
        cleaned_response = response
        
        # 1. Remove <think>...</think> blocks (DeepSeek-R1)
        cleaned_response = re.sub(r'<think>.*?</think>', '', cleaned_response, flags=re.DOTALL)
        
        # 2. Extract from markdown code blocks if present
        code_block = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', cleaned_response, re.DOTALL)
        if code_block:
            cleaned_response = code_block.group(1)
        
        # 3. Find JSON array boundaries as fallback
        json_match = re.search(r'\[.*\]', cleaned_response, re.DOTALL)
        if json_match:
            cleaned_response = json_match.group()
            
        validations = json.loads(cleaned_response)
        
        for v in validations:
            idx = v.get('index', 0) - 1
            if 0 <= idx < len(batch):
                results.append({
                    'retailer': batch[idx]['retailer'],
                    'retailer_name': batch[idx]['retailer_name'],
                    'current_key': batch[idx]['key'],
                    'correct': v.get('correct', None),
                    'confidence': v.get('confidence', 0),
                    'suggested_key': v.get('suggested_key'),
                    'reason': v.get('reason', '')
                })
    except (json.JSONDecodeError, AttributeError) as e:
        print(f"\n❌ JSON Parsing Failed for this batch!")
        print(f"Error: {e}")
        print("Dataset Raw Response Preview (First 500 chars):")
        print("-" * 40)
        print(cleaned_response[:1000])  
        print("-" * 40)
        
        # If parsing fails, mark all as uncertain
        for item in batch:
            results.append({
                'retailer': item['retailer'],
                'retailer_name': item['retailer_name'],
                'current_key': item['key'],
                'correct': None,
                'confidence': 0,
                'reason': f'Failed to parse AI response: {response[:100]}...'
            })
    
    return results


def main():
    print("=" * 60)
    print("🔍 Validating retailer_mapping.yaml with AI")
    print("=" * 60)
    
    # Check if model is available - prefer gemma2:9b (Google)
    model_to_use = MODEL
    result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
    if "gemma2:9b" in result.stdout:
        model_to_use = "gemma2:9b"
    elif "deepseek-r1:8b" in result.stdout:
        model_to_use = "deepseek-r1:8b"
    elif "qwen2.5" in result.stdout:
        model_to_use = "qwen2.5:7b"
    elif "llama3.1" in result.stdout:
        model_to_use = "llama3.1:latest"
    
    print(f"📦 Using model: {model_to_use}")
    print(f"📊 Batch size: {BATCH_SIZE}")
    
    # Load data
    mapping = load_yaml(MAPPING_PATH)
    catalog = load_yaml(CATALOG_PATH)
    
    # Flatten mapping to list of items
    all_items = []
    for retailer, products in mapping.items():
        if isinstance(products, dict):
            for name, key in products.items():
                all_items.append({
                    'retailer': retailer,
                    'retailer_name': name,
                    'key': key
                })
    
    total_items = len(all_items)
    print(f"📝 Total mappings to validate: {total_items}")
    print(f"📦 Number of batches: {(total_items + BATCH_SIZE - 1) // BATCH_SIZE}")
    print()
    
    # Process in batches
    all_results = []
    for i in range(0, total_items, BATCH_SIZE):
        batch = all_items[i:i+BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (total_items + BATCH_SIZE - 1) // BATCH_SIZE
        
        print(f"🔄 Processing batch {batch_num}/{total_batches} ({len(batch)} items)...")
        
        results = validate_batch(batch, catalog, model_to_use)
        all_results.extend(results)
        
        # Count stats for this batch
        correct = sum(1 for r in results if r.get('correct') == True)
        incorrect = sum(1 for r in results if r.get('correct') == False)
        uncertain = sum(1 for r in results if r.get('correct') is None)
        
        print(f"   ✅ Correct: {correct}, ❌ Incorrect: {incorrect}, ❓ Uncertain: {uncertain}")
        
        # Print incorrect mappings immediately
        for r in results:
            if r.get('correct') == False:
                print(f"   ❌ [{r['retailer']}] \"{r['retailer_name']}\"")
                print(f"      Current: {r['current_key']} → Suggested: {r.get('suggested_key', 'N/A')}")
                print(f"      Reason: {r.get('reason', 'N/A')}")
        
        # Delay between batches to avoid overloading
        if i + BATCH_SIZE < total_items:
            time.sleep(DELAY_BETWEEN_BATCHES)
    
    # Summary
    print()
    print("=" * 60)
    print("📊 FINAL SUMMARY")
    print("=" * 60)
    
    total_correct = sum(1 for r in all_results if r.get('correct') == True)
    total_incorrect = sum(1 for r in all_results if r.get('correct') == False)
    total_uncertain = sum(1 for r in all_results if r.get('correct') is None)
    
    print(f"✅ Correct: {total_correct} ({100*total_correct/len(all_results):.1f}%)")
    print(f"❌ Incorrect: {total_incorrect} ({100*total_incorrect/len(all_results):.1f}%)")
    print(f"❓ Uncertain: {total_uncertain} ({100*total_uncertain/len(all_results):.1f}%)")
    
    # Show incorrect mappings
    if total_incorrect > 0:
        print()
        print("❌ INCORRECT MAPPINGS:")
        for r in all_results:
            if r.get('correct') == False:
                print(f"  [{r['retailer']}] \"{r['retailer_name']}\"")
                print(f"    Current: {r['current_key']}")
                if r.get('suggested_key'):
                    print(f"    Suggested: {r['suggested_key']}")
                print(f"    Reason: {r.get('reason', 'N/A')}")
                print()
    
    # Save results
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print(f"💾 Results saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
