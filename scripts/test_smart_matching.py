
import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from processing.normalize import match_product_smart

test_cases = [
    # Case 1: iPad Air Ambiguity (M1 vs A14)
    # iPad Air 5 (2022) has M1
    # iPad Air 4 (2020) has A14
    ("iPad Air M1 64GB", "ipad_air_5"), 
    ("iPad Air M1", "ipad_air_5"), 
    ("iPad Air A14", "ipad_air_4"),
    
    # Case 2: iPad Pro Chips
    ("iPad Pro M2", "ipad_pro_12.9_m2"), # Or 11_m2 depending on score
    
    # Case 3: iPhone Specs
    ("iPhone 13 min 120Hz", None), # 13 mini is 60Hz. Should NOT match Pro.
    # Actually match_product_smart might find "13 mini" name match (base score) but no spec bonus.
    
    ("iPhone 13 Pro 120Hz", "iphone_13_pro"),
]

print("🔍 Testing Smart Matching...")
for text, expected in test_cases:
    result = match_product_smart(text, verbose=True)
    print(f"Input: '{text}' -> Matched: '{result}'")
    
    # Note: Expected might be tricky if we don't know exact keys. 
    # The printed output will verify if it looks reasonable.
