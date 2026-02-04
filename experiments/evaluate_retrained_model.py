import json
import mlx_lm
from mlx_lm import load, generate
from pathlib import Path
from tqdm import tqdm

# Config
ADAPTER_PATH = "experiments/fine_tuning/adapters_llama"
BASE_MODEL = "mlx-community/Llama-3.2-3B-Instruct-4bit"
VALID_DATA = "experiments/fine_tuning/data/valid.jsonl"

def load_model():
    print(f"🤖 Loading model from {BASE_MODEL} with adapters {ADAPTER_PATH}...")
    model, tokenizer = load(BASE_MODEL, adapter_path=ADAPTER_PATH)
    return model, tokenizer

def evaluate():
    model, tokenizer = load_model()
    
    # Load validation data
    with open(VALID_DATA, 'r', encoding='utf-8') as f:
        data = [json.loads(line) for line in f]
        
    print(f"📊 Evaluating on {len(data)} samples...")
    
    correct = 0
    total = 0
    errors = []
    
    for item in tqdm(data):
        messages = item['messages']
        user_content = next(m['content'] for m in messages if m['role'] == 'user')
        expected = next(m['content'] for m in messages if m['role'] == 'assistant')
        
        # Construct Prompt
        prompt = tokenizer.apply_chat_template([
            {"role": "system", "content": "You are a product matching assistant. Map the retailer product name to the correct canonical key."},
            {"role": "user", "content": user_content}
        ], tokenize=False, add_generation_prompt=True)
        
        response = generate(model, tokenizer, prompt=prompt, max_tokens=50, verbose=False)
        response = response.strip()
        
        if response == expected:
            correct += 1
        else:
            errors.append({
                "input": user_content,
                "expected": expected,
                "got": response
            })
        total += 1
        
    accuracy = (correct / total) * 100
    print(f"\n✅ Accuracy: {accuracy:.2f}% ({correct}/{total})")
    
    if errors:
        print("\n❌ Sample Errors:")
        for e in errors[:10]:
            print(f"  Input: {e['input']}")
            print(f"  Exp:   {e['expected']}")
            print(f"  Got:   {e['got']}")
            print("-" * 30)
            
if __name__ == "__main__":
    evaluate()
