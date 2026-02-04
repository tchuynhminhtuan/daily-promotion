
import sys
import os
import json
from pathlib import Path

# Setup paths
BASE_DIR = Path(os.getcwd())
sys.path.append(str(BASE_DIR / "src"))

# Import AI logic
try:
    from processing.normalize import load_ai_model, _AI_MODEL, _AI_TOKENIZER
except ImportError:
    sys.path.append(str(BASE_DIR))
    from processing.normalize import load_ai_model, _AI_MODEL, _AI_TOKENIZER

def extract_promo(promo_text):
    if not promo_text or len(str(promo_text)) < 10:
        return None
        
    # Lazy load
    from mlx_lm import generate
    global _AI_MODEL, _AI_TOKENIZER
    if not _AI_MODEL:
        load_ai_model()
        from processing.normalize import _AI_MODEL, _AI_TOKENIZER # Re-import global var

    # Prompt Engineering for JSON Extraction
    SYSTEM_PROMPT = """You are an AI assistant that extracts structured data from promotion text.
    Output ONLY valid JSON with these keys:
    - promo_type: Main type (e.g., "Discount", "Gift", "Installment")
    - discount_value: Numeric value of discount (if any)
    - gifts: List of gift items
    - requirements: Conditions (e.g., "Via VNPay", "Old for New")
    - expiry: Expiry date if mentioned
    """
    
    prompt = f"""<|im_start|>system
{SYSTEM_PROMPT}<|im_end|>
<|im_start|>user
Extract this text:
"{promo_text}"<|im_end|>
<|im_start|>assistant
"""
    
    response = generate(_AI_MODEL, _AI_TOKENIZER, prompt=prompt, max_tokens=150, verbose=False)
    return response.strip()

def run_demo():
    print("🚀 Initializing Llama 3B for Promo Extraction Demo...")
    if not load_ai_model():
        print("❌ Failed to load model.")
        return

    # Real Examples from 1-fpt.csv
    examples = [
        # Example 1: Complex FPT Promo
        """Khuyến mãi được hưởng
Tặng túi lộc 2,700,000đ áp dụng đến 14/02
Đặc quyền tặng gói dịch vụ Apple Music và Fitness+ 3 tháng 
Lì xì đến 1,000,000đ mua Gia Dụng, Điện Máy, Phụ Kiện 
Lì xì 500,000đ mua Tai nghe AirPods 
Lì xì thêm đến 2,5 triệu khi mua kèm SIM FPT 
Trả góp 0%""",
        
        # Example 2: Payment Promo
        """Giảm ngay 800,000đ cho đơn từ 8 triệu khi thanh toán qua thẻ Visa SCB.
HSD: 30/06/2026
Giảm ngay 50% tối đa 100.000đ cho Khách hàng mới qua Kredivo
HSD: 28/02/2026""",

        # Example 3: Simple Gift
        """Tặng phiếu mua hàng 50,000đ khi mua sim FPT kèm máy
Giảm 5% mua camera cho đơn hàng Điện thoại/ Tablet"""
    ]

    for i, text in enumerate(examples):
        print(f"\n--- Example {i+1} ---")
        print(f"📝 Raw Text:\n{text[:100]}...") # Truncate for display
        
        try:
            json_out = extract_promo(text)
            print(f"💡 AI Extracted JSON:\n{json_out}")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    run_demo()
