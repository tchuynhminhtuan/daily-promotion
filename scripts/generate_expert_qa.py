
import sqlite3
import json
import random
from pathlib import Path

DB_PATH = Path("catalog/price_history.db")
OUTPUT_PATH = Path("experiments/fine_tuning/data/training_data_v3.jsonl")

# Templates for generating questions
# {name} will be replaced by product name
# {val} will be replaced by the spec value
TEMPLATES = {
    "chip": [
        ("What chip does the {name} use?", "The {name} is powered by the {val}."),
        ("What processor is in {name}?", "{name} features the {val}."),
        ("Does {name} have a powerful chip?", "Yes, it runs on the {val}."),
    ],
    "display": [
        ("What is the screen size of {name}?", "{name} has a {val}."),
        ("Tell me about the display of {name}.", "It features a {val}."),
        ("Is the {name} screen good?", "It comes with a {val}."),
    ],
    "back_camera": [
        ("What camera does {name} have?", "It is equipped with {val}."),
        ("Describe the rear camera of {name}.", "{val}."),
    ],
    "security": [
        ("Does {name} have Face ID?", "The security specs are: {val}."), # val might say Touch ID
        ("How do I unlock {name}?", "It uses {val}."),
    ]
}

def clean_spec(text):
    if not text: return None
    # Remove pipes used for storage in DB string
    text = text.replace("|", "\n-")
    return text.strip()
def generate_qa():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    products = cursor.execute("""
        SELECT p.name, p.category, s.chip, s.display, s.back_camera, s.security 
        FROM products p 
        JOIN specs s ON p.id = s.product_id
    """).fetchall()
    
    data = []
    
    print(f"🧠 Generating questions for {len(products)} products...")
    
    for p in products:
        name = p['name']
        
        # for each spec column
        for col, tpls in TEMPLATES.items():
            val = clean_spec(p[col])
            if not val or val == "—" or len(val) < 3:
                continue
                
            # Randomly pick a template or generate all?
            # Let's generate all to maximize data (we'll filter/split later)
            for q_tpl, a_tpl in tpls:
                # Basic cleaning of cleaner value for sentence flow
                # If val starts with "-", remove it for sentence start? 
                # Keep it simple.
                
                question = q_tpl.format(name=name)
                answer = a_tpl.format(name=name, val=val)
                
                # ChatML Format
                entry = {
                    "messages": [
                        {"role": "system", "content": "You are an Apple expert assistant."},
                        {"role": "user", "content": question},
                        {"role": "assistant", "content": answer}
                    ]
                }
                data.append(entry)
                
        # Aggregate "Tell me specs" question
        specs_summary = []
        if p['chip']: specs_summary.append(f"**Chip**: {clean_spec(p['chip'])}")
        if p['display']: specs_summary.append(f"**Display**: {clean_spec(p['display'])}")
        if p['back_camera']: specs_summary.append(f"**Camera**: {clean_spec(p['back_camera'])}")
        
        if specs_summary:
            full_ans = f"Here are the specs for {name}:\n" + "\n".join(specs_summary)
            entry = {
                "messages": [
                    {"role": "system", "content": "You are an Apple expert assistant."},
                    {"role": "user", "content": f"Show me specs for {name}"},
                    {"role": "assistant", "content": full_ans}
                ]
            }
            data.append(entry)

    conn.close()
    
    # Save
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            
    print(f"✅ Generated {len(data)} expert QA pairs in {OUTPUT_PATH}")

if __name__ == "__main__":
    generate_qa()
