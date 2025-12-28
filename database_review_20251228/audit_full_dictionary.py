
import json
import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'code'))

from normalize_ml import clean_string, get_blocking_constraints, get_expanded_models, get_historical_median_prices, load_raw_data # Import helper logic
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# We'll redefine a simple version of train_and_predict logic for self-audit
def audit_mappings(mappings_file="mappings_candidate.json", db_file="apple_products_db.json"):
    if not os.path.exists(mappings_file):
        print(f"❌ {mappings_file} not found.")
        return
    
    with open(mappings_file, 'r') as f:
        mappings = json.load(f)
        
    with open(db_file, 'r') as f:
        db_data = json.load(f)
        
    official_keys = get_expanded_models(db_data)
    clean_official = [clean_string(k) for k in official_keys]
    official_constraints = [get_blocking_constraints(k) for k in clean_official]
    
    # 1. Prepare ML Model
    vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4))
    vectorizer.fit(clean_official)
    tfidf_official = vectorizer.transform(clean_official)
    
    # 2. Prepare Price Data
    history_meds = get_historical_median_prices()
    latest_data = load_raw_data()
    price_map = {}
    if not latest_data.empty:
        price_map = pd.Series(latest_data.price.values, index=latest_data.name).to_dict()

    print(f"🕵️ Auditing {len(mappings)} Product Groups...")
    suspicious = []

    for target_key, raw_names in mappings.items():
        if target_key == "_REVIEW_NEEDED_": continue
        
        hist_med = history_meds.get(target_key)
        
        for raw in raw_names:
            raw_clean = clean_string(raw)
            raw_cons = get_blocking_constraints(raw_clean)
            
            # A. ML Consistency Check
            tfidf_raw = vectorizer.transform([raw_clean])
            scores = cosine_similarity(tfidf_raw, tfidf_official)[0]
            best_idx = np.argmax(scores)
            ml_pred = official_keys[best_idx]
            
            # Check if current target matches ML's best choice (considering blocking)
            # Find best match that passes constraints
            sorted_indices = np.argsort(scores)[::-1]
            constrained_ml = None
            for idx in sorted_indices[:15]:
                if scores[idx] < 0.2: break
                if raw_cons.issubset(official_constraints[idx]):
                    constrained_ml = official_keys[idx]
                    break
            
            drift = False
            if constrained_ml and constrained_ml != target_key:
                drift = True
            
            # B. Price Regression Check
            curr_p = price_map.get(raw, 0)
            price_issue = False
            if curr_p > 0 and hist_med:
                if curr_p < hist_med * 0.4 or curr_p > hist_med * 2.5: # 2.5 buffer for Pro Max vs regular
                    price_issue = True
            
            if drift or price_issue:
                suspicious.append({
                    "raw": raw,
                    "current_target": target_key,
                    "ml_suggested": constrained_ml,
                    "price_issue": price_issue,
                    "curr_price": curr_p,
                    "median_price": hist_med
                })

    if suspicious:
        print(f"⚠️ Found {len(suspicious)} suspicious mappings:")
        for s in suspicious:
            print(f"- '{s['raw']}'")
            print(f"  Mapped to: {s['current_target']}")
            if s['ml_suggested'] and s['ml_suggested'] != s['current_target']:
                print(f"  ML suggests: {s['ml_suggested']}")
            if s['price_issue']:
                print(f"  💰 Price Variance: {s['curr_price']:,} ₫ vs Median {s['median_price']:,} ₫")
            print("-" * 30)
    else:
        print("✅ All mappings consistent with ML and Price logic.")

if __name__ == "__main__":
    audit_mappings()
