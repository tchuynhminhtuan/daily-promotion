"""
Centralized Configuration for Retail Intelligence Subproject
"""

import os

# Đường dẫn thư mục
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
HYBRID_DATA_DIR = os.path.join(DATA_DIR, "hybrid")
PREDICTIONS_DIR = os.path.join(DATA_DIR, "predictions")
MODELS_DIR = os.path.join(os.path.dirname(__file__), "models", "saved_models")

# Tạo sẵn thư mục nếu chưa tồn tại
os.makedirs(HYBRID_DATA_DIR, exist_ok=True)
os.makedirs(PREDICTIONS_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

# Danh mục Apple trên Thế Giới Di Động
CATEGORIES = {
    "iPhone": "https://www.thegioididong.com/dtdd-apple-iphone",
    "MacBook": "https://www.thegioididong.com/laptop-apple-macbook",
    "Apple Watch": "https://www.thegioididong.com/dong-ho-thong-minh-apple",
    "iPad": "https://www.thegioididong.com/may-tinh-bang-apple-ipad",
    "AirPods": "https://www.thegioididong.com/tai-nghe-apple"
}

# API nội bộ kiểm tra tồn kho theo cửa hàng
STORE_API_URL = "https://api.thegioididong.com/gw/bus-tgdd-tmdt/api/Store/GetStoreByDeliveryPolicy"

# HTTP Headers
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
}

# Cấu hình Feature Engineering
CATEGORICAL_FEATURES = ["Category", "Generation", "Color_Group"]
NUMERIC_FEATURES = [
    "Price_Million",
    "Storage_GB",
    "RAM_GB",
    "Log_Rating_Count",
    "Rating_Score_Num",
    "Direct_Discount_VND",
    "Trade_In_Subsidy_VND",
    "Min_Monthly_Payment_12M",
    "Installment_0_Percent",
    "Has_Demo",
    "Sample_Display_Total"
]
