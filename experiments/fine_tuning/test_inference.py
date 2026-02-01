
import sys
from mlx_lm import load, generate

def main():
    adapter_path = "experiments/fine_tuning/adapters"
    base_model = "Qwen/Qwen2.5-0.5B-Instruct"
    
    print(f"Loading model {base_model} with adapters from {adapter_path}...")
    model, tokenizer = load(base_model, adapter_path=adapter_path)
    
    # Test cases (Some seen, some unseen variations)
    test_products = [
        "Apple Watch SE 3 40mm (GPS) Viền Nhôm Dây Cao Su",
        "iPhone 13 128GB Chính Hãng",
        "iPad Pro M4 11 inch Wifi 2TB Nano",
        "MacBook Air M2 2024 8CPU 8GPU 16GB 256GB" 
    ]
    
    SYSTEM_PROMPT = "You are a product matching assistant. Map the retailer product name to the correct canonical key."
    
    print("\n=== INFERENCE TEST ===")
    for product in test_products:
        prompt = f"<|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>\n<|im_start|>user\nMap this product: {product}<|im_end|>\n<|im_start|>assistant\n"
        
        response = generate(model, tokenizer, prompt=prompt, max_tokens=50, verbose=False)
        print(f"Input:  {product}")
        print(f"Output: {response.strip()}")
        print("-" * 40)

if __name__ == "__main__":
    main()
