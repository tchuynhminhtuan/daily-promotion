
import sys
from mlx_lm import load, generate

def main():
    adapter_path = "experiments/fine_tuning/adapters"
    base_model = "Qwen/Qwen2.5-0.5B-Instruct"
    
    print(f"Loading model {base_model} with adapters from {adapter_path}...")
    try:
        model, tokenizer = load(base_model, adapter_path=adapter_path)
    except Exception as e:
        print(f"Error loading model: {e}")
        return

    # Specific "Hallucination" Traps to Verify
    test_questions = [
        # 1. iPad Air M3 (Using exact name from training)
        "What chip does the iPad Air 11-inch (M3) have?",
        "Describe the display of iPad Air 13-inch (M3).",
        
        # 2. Apple Watch Series 11 (Was hallucinating S11, should be S10)
        "What chip is in Apple Watch Series 11?",
        
        # 3. New Data Check (iPad Pro M5)
        # Assuming name in DB is iPad Pro 11-inch (M5)
        "What is special about the iPad Pro 11-inch (M5) display?",
    ]
    
    SYSTEM_PROMPT = "You are an Apple expert assistant. Answer questions based on your training data."
    
    print("\n=== HALLUCINATION CHECK (M3/M5/S11) ===")
    for question in test_questions:
        prompt = f"<|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>\n<|im_start|>user\n{question}<|im_end|>\n<|im_start|>assistant\n"
        
        response = generate(model, tokenizer, prompt=prompt, max_tokens=150, verbose=False)
        print(f"\nQ: {question}")
        print(f"A: {response.strip()}")
        print("-" * 40)

if __name__ == "__main__":
    main()
