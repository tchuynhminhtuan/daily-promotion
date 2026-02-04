
import sys
from mlx_lm import load, generate

def main():
    adapter_path = "experiments/fine_tuning/adapters_llama"
    base_model = "mlx-community/Llama-3.2-3B-Instruct-4bit"
    
    print(f"Loading model {base_model} with adapters from {adapter_path}...")
    model, tokenizer = load(base_model, adapter_path=adapter_path)
    
    # Test cases (Some seen, some unseen variations)
    # Test cases: 10 Challenging Items (Edge cases, suffixes, new models)
    test_products = [
        # 1. Nano Texture Edge Case
        "Diện thoại iPad Pro M4 11 inch Wifi 2TB Nano", 
        "iPad Pro M4 13 inch Wifi + 5G 2TB Nano-texture glass",

        # 2. Chip Pro/Max Distinctions
        "Laptop MacBook Pro M3 Pro 16 inch 18GB/512GB Chính Hãng",
        "MacBook Pro 14 M4 Max 14CPU 32GPU 36GB 1TB Nano Chính hãng",

        # 3. Apple Watch Series 11 (Titanium vs Aluminum)
        "Apple Watch Series 11 Viền Titan Cellular 46mm Dây Milanese M/L",
        "Apple Watch Series 11 42mm (GPS) Viền nhôm - Dây cao su S/M",

        # 4. iPad Mini 7 (Pro chip confusion)
        "Tai nghe iPad Mini 7 8.3 inch WiFi (128GB) VN/A",

        # 5. iPad A16 (New Base Model)
        "iPad A16 11 inch 5G (512GB)",

        # 6. Ambiguous "SE" (Watch SE 3 LTE)
        "Apple Watch SE 3 LTE 44mm Viền Nhôm Dây Cao Su",
        
        # 7. Complex Old Model (Air M1 vs M2)
        "Apple MacBook Air 13 256GB 2020",
    ]
    
    SYSTEM_PROMPT = "You are a product matching assistant. Map the retailer product name to the correct canonical key."
    
    print("\n=== INFERENCE TEST ===")
    for product in test_products:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Map this product: {product}"}
        ]
        prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        
        response = generate(model, tokenizer, prompt=prompt, max_tokens=50, verbose=False)
        print(f"Input:  {product}")
        print(f"Output: {response.strip()}")
        print("-" * 40)

if __name__ == "__main__":
    main()
