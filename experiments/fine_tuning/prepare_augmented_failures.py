
import json
import random
from pathlib import Path

# Goal: Generate aggressive variations for specific failure cases to force model learning.

OUTPUT_FILE = "experiments/fine_tuning/data/augmented_failures.jsonl"

def generate_variations(product_name, canonical_key, category):
    data = []
    
    # Common noises/prefixes/suffixes found in Vietnamese e-commerce
    prefixes = [
        "Điện thoại", "Máy tính bảng", "Laptop", "Đồng hồ", "Mới 100%", "Chính hãng", 
        "Apple", "Trả góp 0%", "Giá rẻ", "VN/A", "Fullbox", "Siêu phẩm"
    ]
    suffixes = [
        "Chính hãng", "VN/A", "Mới", "Box", "Full Seal", "Bảo hành 12T", 
        "Giá tốt", "Trả góp", "Khuyến mãi", "Hot", "Nano", "2024", "2025"
    ]
    
    # 1. Base Variation
    data.append({"messages": [
        {"role": "system", "content": "You are a product matching assistant. Map the retailer product name to the correct canonical key."},
        {"role": "user", "content": f"Map this product: {product_name}"},
        {"role": "assistant", "content": canonical_key}
    ]})
    
    # 2. Case variations (lower, upper, mixed)
    for _ in range(3):
        p_var = product_name
        if random.random() > 0.5: p_var = p_var.lower()
        elif random.random() > 0.5: p_var = p_var.upper()
        
        data.append({"messages": [
            {"role": "system", "content": "You are a product matching assistant. Map the retailer product name to the correct canonical key."},
            {"role": "user", "content": f"Map this product: {p_var}"},
            {"role": "assistant", "content": canonical_key}
        ]})

    # 3. Aggressive Noise Injection (Prefix/Suffix)
    for _ in range(5):
        prefix = random.choice(prefixes) if random.random() > 0.3 else ""
        suffix = random.choice(suffixes) if random.random() > 0.3 else ""
        
        # Sometimes stick words together or map differently
        text = f"{prefix} {product_name} {suffix}".strip()
        text = " ".join(text.split()) # normalize spaces
        
        data.append({"messages": [
            {"role": "system", "content": "You are a product matching assistant. Map the retailer product name to the correct canonical key."},
            {"role": "user", "content": f"Map this product: {text}"},
            {"role": "assistant", "content": canonical_key}
        ]})
        
    return data

def main():
    print("🚀 Generating Augmented Failure Cases...")
    all_rows = []
    
    # === TARGET 1: iPad A16 5G Bias ===
    # Problem: Model predicts "wifi" because training data might be dominated by wifi or ambiguous labels.
    # Solution: Force "5G", "LTE", "Cellular", "Lắp sim" -> lte key
    keywords_5g = ["5G", "LTE", "Cellular", "Wifi + 5G", "Wifi + Cellular", "5G Wifi", "Lắp sim"]
    
    for kw in keywords_5g:
        # Generate varied inputs
        items = [
            f"iPad A16 11 inch {kw} 128GB",
            f"iPad A16 11 inch {kw} 256GB",
            f"iPad A16 11\" {kw} (512GB)",
            f"Máy tính bảng iPad A16 {kw}"
        ]
        for item in items:
            all_rows.extend(generate_variations(item, "ipad_a16_lte", "iPad"))

    # === TARGET 2: Nano Texture ===
    # Problem: "Nano" at end of string often ignored.
    # Solution: Add many examples where "Nano" is the critical differentiator.
    nano_items = [
        ("iPad Pro M4 11 inch Wifi 1TB Nano", "ipad_pro_11_m4_wifi_nano"),
        ("iPad Pro M4 13 inch Wifi 2TB Nano texture", "ipad_pro_13_m4_wifi_nano"),
        ("iPad Pro M4 11\" 5G 1TB Màn hình Nano", "ipad_pro_11_m4_lte_nano"),
        ("MacBook Pro 14 M4 Max 1TB Nano", "macbook_pro_14_m4_max_nano")
    ]
    for name, key in nano_items:
         all_rows.extend(generate_variations(name, key, "Mac/iPad"))

    # === TARGET 3: Chip Nuance (M3 vs M3 Pro) ===
    # Problem: "MacBook Pro M3 Pro" mapped to "M3" base.
    chip_items = [
        ("MacBook Pro 14 M3 Pro 18GB/512GB", "macbook_pro_14_m3_pro_max"),
        ("MacBook Pro 16 M3 Pro 36GB", "macbook_pro_16_m3_pro_max"),
        ("MacBook Pro 14 M3 Max 36GB", "macbook_pro_14_m3_pro_max")
    ]
    for name, key in chip_items:
        all_rows.extend(generate_variations(name, key, "Mac"))

    # Shuffle and Save
    random.shuffle(all_rows)
    
    # Create directory if needed
    Path(OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for row in all_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            
    print(f"✅ Generated {len(all_rows)} augmented samples for hard cases.")
    print(f"📁 Saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
