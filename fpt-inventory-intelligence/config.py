"""
Centralized Configuration for FPT Retail Inventory Intelligence Engine
Phân hệ chuyên biệt cho mạng lưới FPT Shop & F.Studio by FPT (Ecosystem Apple)
"""

import os

# Đường dẫn thư mục gốc độc lập
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
MASTER_DIR = os.path.join(DATA_DIR, "master")
RAW_DATA_DIR = os.path.join(DATA_DIR, "raw")
PREDICTIONS_DIR = os.path.join(DATA_DIR, "predictions")
REPORTS_DIR = os.path.join(DATA_DIR, "reports")
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")

# Tạo sẵn các thư mục cần thiết
os.makedirs(MASTER_DIR, exist_ok=True)
os.makedirs(RAW_DATA_DIR, exist_ok=True)
os.makedirs(PREDICTIONS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# File lưu trữ danh bạ Master Stores FPT (602 shop có GPS, địa chỉ cũ/mới)
MASTER_STORES_FILE = os.path.join(MASTER_DIR, "fpt_master_stores.json")
SLUGS_CACHE_FILE = os.path.join(MASTER_DIR, "apple_product_slugs.json")

# API Gateways của FPT Shop
API_GATEWAY_BEFORE_ORDER = "https://papi.fptshop.com.vn/gw/v1/public/bff-before-order/"
API_GATEWAY_SMART = "https://papi.fptshop.com.vn/gw/v1/public/bff-smart-api/"

# Endpoint chi tiết
VARIANT_API_URL = f"{API_GATEWAY_BEFORE_ORDER}product/variant"
TRADE_IN_API_URL = f"{API_GATEWAY_BEFORE_ORDER}product/trade-in"
SHOPS_API_URL = f"{API_GATEWAY_SMART}order-promising/shops"
PICKUP_API_URL = f"{API_GATEWAY_SMART}order-promising/pick-up-at-shop"
PROVINCES_API_URL = f"{API_GATEWAY_SMART}order-promising/province-dsms"

# Headers chuẩn hóa cho 2 kênh
BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Origin": "https://fptshop.com.vn",
    "Referer": "https://fptshop.com.vn/",
    "Accept": "application/json",
}

# Kênh 1: Toàn bộ hệ thống FPT Shop
HEADERS_FPTSHOP = {**BASE_HEADERS, "order-channel": "1"}

# Kênh 12: Hệ thống cao cấp Apple F.Studio by FPT
HEADERS_FSTUDIO = {**BASE_HEADERS, "order-channel": "12"}

# 34 mã tỉnh thành chuẩn Tổng cục Thống kê (GSO) có siêu thị FPT đang hoạt động
ACTIVE_PROVINCES = [
    "01", "04", "08", "11", "12", "14", "15", "19", "20", "22",
    "24", "25", "31", "33", "37", "38", "40", "42", "44", "46",
    "48", "51", "52", "56", "66", "68", "75", "79", "80", "82",
    "86", "91", "92", "96"
]

# Tên các tỉnh trọng điểm dùng cho báo cáo nhanh
KEY_PROVINCES = {
    "79": "TP. Hồ Chí Minh",
    "01": "TP. Hà Nội",
    "48": "Đà Nẵng",
    "31": "Hải Phòng",
    "92": "Cần Thơ",
    "66": "Đắk Lắk",
    "68": "Lâm Đồng",
    "75": "Đồng Nai"
}

# Danh mục sản phẩm Apple trên FPT Shop
CATEGORY_URLS = {
    "iPhone": "https://fptshop.com.vn/dien-thoai/apple-iphone",
    "iPad": "https://fptshop.com.vn/may-tinh-bang/apple-ipad",
    "MacBook": "https://fptshop.com.vn/may-tinh-xach-tay/apple-macbook",
    "Apple Watch": "https://fptshop.com.vn/smartwatch/apple",
    "AirPods": "https://fptshop.com.vn/phu-kien/apple"
}
