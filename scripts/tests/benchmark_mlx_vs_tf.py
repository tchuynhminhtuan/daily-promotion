"""
Benchmark: MLX vs Transformers for Qwen 2.5-0.5B
"""
import time

# Test prompts
TEST_PROMPTS = [
    "iPhone 16 Pro Max 256GB",
    "Apple Watch Series 11 GPS 42mm",
    "MacBook Air M4 13 inch 16GB/512GB",
    "iPad Pro M5 11 inch WiFi 256GB",
    "AirPods Pro 3 2025",
]

def benchmark_mlx():
    """Benchmark MLX-LM"""
    print("\n🍎 Testing MLX-LM...")
    try:
        from mlx_lm import load, generate
        
        start_load = time.time()
        # Load with adapter path - MLX handles base model automatically
        adapter_path = "experiments/fine_tuning/adapters"
        model, tokenizer = load("Qwen/Qwen2.5-0.5B-Instruct", adapter_path=adapter_path)
        load_time = time.time() - start_load
        print(f"  Model load time: {load_time:.2f}s")
        
        total_time = 0
        for prompt in TEST_PROMPTS:
            full_prompt = f"Product: {prompt}\nKey:"
            start = time.time()
            response = generate(model, tokenizer, prompt=full_prompt, max_tokens=20)
            elapsed = time.time() - start
            total_time += elapsed
            key = response.split("Key:")[-1].strip().split()[0] if "Key:" in response else response.strip()
            print(f"  {prompt[:30]:<30} → {key:<30} ({elapsed:.2f}s)")
        
        avg_time = total_time / len(TEST_PROMPTS)
        print(f"\n  ✅ MLX Average: {avg_time:.2f}s per inference")
        return avg_time
        
    except Exception as e:
        print(f"  ❌ MLX Error: {e}")
        return None

def benchmark_transformers():
    """Benchmark Transformers + PyTorch"""
    print("\n🤗 Testing Transformers + PyTorch...")
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import PeftModel
        import torch
        
        # Check device
        device = "mps" if torch.backends.mps.is_available() else "cpu"
        print(f"  Using device: {device}")
        
        start_load = time.time()
        base_model = "Qwen/Qwen2.5-0.5B-Instruct"
        adapter_path = "experiments/fine_tuning/adapters"
        
        tokenizer = AutoTokenizer.from_pretrained(base_model)
        model = AutoModelForCausalLM.from_pretrained(base_model, torch_dtype=torch.float16).to(device)
        # Load LoRA adapter
        model = PeftModel.from_pretrained(model, adapter_path)
        load_time = time.time() - start_load
        print(f"  Model load time: {load_time:.2f}s")
        
        total_time = 0
        for prompt in TEST_PROMPTS:
            full_prompt = f"Product: {prompt}\nKey:"
            start = time.time()
            
            inputs = tokenizer(full_prompt, return_tensors="pt").to(device)
            with torch.no_grad():
                outputs = model.generate(**inputs, max_new_tokens=20, pad_token_id=tokenizer.eos_token_id)
            response = tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            elapsed = time.time() - start
            total_time += elapsed
            key = response.split("Key:")[-1].strip().split()[0] if "Key:" in response else response.strip()
            print(f"  {prompt[:30]:<30} → {key:<30} ({elapsed:.2f}s)")
        
        avg_time = total_time / len(TEST_PROMPTS)
        print(f"\n  ✅ Transformers Average: {avg_time:.2f}s per inference")
        return avg_time
        
    except Exception as e:
        print(f"  ❌ Transformers Error: {e}")
        return None

if __name__ == "__main__":
    print("=" * 60)
    print("🔥 Qwen 2.5-0.5B Benchmark: MLX vs Transformers")
    print("=" * 60)
    
    mlx_time = benchmark_mlx()
    tf_time = benchmark_transformers()
    
    print("\n" + "=" * 60)
    print("📊 RESULTS:")
    if mlx_time: print(f"  MLX-LM:       {mlx_time:.2f}s avg")
    if tf_time: print(f"  Transformers: {tf_time:.2f}s avg")
    if mlx_time and tf_time:
        ratio = tf_time / mlx_time
        print(f"  Ratio: Transformers is {ratio:.1f}x slower than MLX")
    print("=" * 60)
