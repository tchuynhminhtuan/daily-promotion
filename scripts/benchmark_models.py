import glob
import pandas as pd
import random
from mlx_lm import load, generate
import csv

# 1. Load Data
files = glob.glob('data/raw/2026-01-31-specs/*.csv')
samples = []

print("📊 Sampling data...")
for f in files:
    try:
        # Detect delimiter (FPT/MW use ',', others might use ';')
        if 'hoangha' in f or 'ddv' in f or 'cps' in f or 'viettel' in f:
            sep = ';'
        else:
            sep = ','
            
        df = pd.read_csv(f, sep=sep, on_bad_lines='skip')
        
        # Normalize column names
        cols = [c.lower() for c in df.columns]
        df.columns = cols
        
        if 'product_name' in df.columns:
            names = df['product_name'].dropna().unique().tolist()
            # Pick 5 random
            if len(names) > 5:
                picks = random.sample(names, 5)
            else:
                picks = names
                
            retailer = f.split('/')[-1].split('-')[1]
            for p in picks:
                samples.append({'Retailer': retailer, 'Product_Name': p})
    except Exception as e:
        print(f"⚠️ Error reading {f}: {e}")

print(f"✅ Loaded {len(samples)} samples.")

# 2. Results Container
results = {s['Product_Name']: {'Retailer': s['Retailer'], 'Input': s['Product_Name']} for s in samples}

# 3. Test Qwen 0.5B
print("\n🤖 Loading Qwen 2.5-0.5B (Fine-tuned)...")
model_qwen, tokenizer_qwen = load(
    'Qwen/Qwen2.5-0.5B-Instruct',
    adapter_path='experiments/fine_tuning/adapters'
)

print("🚀 Running Qwen Inference...")
for s in samples:
    name = s['Product_Name']
    messages = [{'role': 'user', 'content': name}]
    prompt = tokenizer_qwen.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
    output = generate(model_qwen, tokenizer_qwen, prompt=prompt, max_tokens=50, verbose=False)
    key = output.split('<|im_end|>')[0].strip()
    results[name]['Qwen_0.5B'] = key

# Free memory (not perfect in python but helps)
del model_qwen
del tokenizer_qwen

# 4. Test Llama 3.2-3B
print("\n🦙 Loading Llama 3.2-3B (Fine-tuned)...")
try:
    model_llama, tokenizer_llama = load(
        'mlx-community/Llama-3.2-3B-Instruct-4bit',
        adapter_path='experiments/fine_tuning/adapters_llama'
    )
    
    print("🚀 Running Llama Inference...")
    for s in samples:
        name = s['Product_Name']
        messages = [{'role': 'user', 'content': name}]
        prompt = tokenizer_llama.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
        output = generate(model_llama, tokenizer_llama, prompt=prompt, max_tokens=50, verbose=False)
        key = output.split('<|eot_id|>')[0].strip()
        results[name]['Llama_3B'] = key

except Exception as e:
    print(f"❌ Failed to load Llama: {e}")
    for s in samples:
         results[s['Product_Name']]['Llama_3B'] = "ERROR"

# 5. Save & Print
out_file = 'model_benchmark_results.csv'
with open(out_file, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['Retailer', 'Input', 'Qwen_0.5B', 'Llama_3B'])
    writer.writeheader()
    for name, data in results.items():
        writer.writerow(data)

print(f"\n✅ Benchmark saved to {out_file}")

# Print comparison
print("\n🔍 Comparison (Sample):")
print(f"{'Product Name':<40} | {'Qwen 0.5B':<30} | {'Llama 3B':<30}")
print("-" * 105)
for i, (name, data) in enumerate(results.items()):
    if i >= 15: break # Show first 15
    print(f"{name[:40]:<40} | {data['Qwen_0.5B']:<30} | {data['Llama_3B']:<30}")
