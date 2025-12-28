
import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'code'))

from normalize_ml import clean_string, get_blocking_constraints, KNOWN_MODELS, SIMILARITY_THRESHOLD
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

debug_items = [
    "AirPods 4 (chống ồn)",
    "Apple Watch SE 2023",
    "MacBook Air 13 inch M2 16GB/256GB",
    "MacBook Air M1 13 inch (8GB/256GB)",
    "MacBook Air M2 2024 13-inch 16GB/256GB Chính Hãng",
    "Tai nghe AirPods 4 bản Chủ Động Khử Tiếng Ồn",
    "iPad (A16) 11 inch WIFI 128GB",
    "iPad Air (Gen 6) M2 11 inch WIFI 1TB",
    "iPhone Air 512GB",
    "iPad Pro M5 11 inch WIFI 5G 1TB Nano"
]

def debug_matching():
    official_keys = KNOWN_MODELS
    clean_official = [clean_string(k) for k in official_keys]
    official_constraints = [get_blocking_constraints(k) for k in clean_official]
    
    vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4))
    vectorizer.fit(clean_official + [clean_string(r) for r in debug_items])
    tfidf_official = vectorizer.transform(clean_official)
    
    for raw in debug_items:
        print(f"\n🔍 Debugging: '{raw}'")
        raw_clean = clean_string(raw)
        raw_cons = get_blocking_constraints(raw_clean)
        print(f"   Clean: {raw_clean}")
        print(f"   Constraints: {raw_cons}")
        
        tfidf_raw = vectorizer.transform([raw_clean])
        scores = cosine_similarity(tfidf_raw, tfidf_official)[0]
        sorted_indices = np.argsort(scores)[::-1]
        
        found = False
        print("   Top Candidates:")
        for i in range(10):
            idx = sorted_indices[i]
            score = scores[idx]
            cand = official_keys[idx]
            cand_cons = official_constraints[idx]
            passed = raw_cons.issubset(cand_cons)
            
            status = "✅ PASS" if passed else "❌ BLOCK"
            if score < SIMILARITY_THRESHOLD: status = "⚪️ LOW SCORE"
            
            print(f"   - {score:.3f} | {status} | Constraints: {cand_cons} | {cand}")
            
            if passed and score >= SIMILARITY_THRESHOLD:
                if not found:
                    print(f"   ⭐️ Winning Match: {cand}")
                    found = True
        
        if not found:
            print("   ⚠️ NO VALID MATCH FOUND")

if __name__ == "__main__":
    debug_matching()
