"""
Viettel Store Inventory Intelligence - Central Configuration
=============================================================
Centralized architecture configuration module for Viettel Store reverse engineering,
ASMX Web Services, AjaxAction handlers, Microservice Gateway proxies, and master paths.
"""

from pathlib import Path

# Project Directory Layout
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
MASTER_DIR = DATA_DIR / "master"
RAW_DIR = DATA_DIR / "raw"
SNAPSHOTS_DIR = DATA_DIR / "snapshots"
REPORTS_DIR = DATA_DIR / "reports"
DOCS_DIR = PROJECT_ROOT / "docs"

# Ensure runtime directories exist
for directory in [DATA_DIR, MASTER_DIR, RAW_DIR, SNAPSHOTS_DIR, REPORTS_DIR, DOCS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# API Host & Gateway Endpoints
VT_HOST = "https://viettelstore.vn"
CDN_HOST = "https://cdn.viettelstore.vn"

# 1. ASMX Web Service (JSON-RPC for ERP Pricing & Nationwide Stock)
ASMX_ENDPOINT = f"{VT_HOST}/Site/_Sys/ajax.asmx"
ASMX_GET_PRICE_STOCK = f"{ASMX_ENDPOINT}/ProductRule_GetPriceByRule"

# 2. Ajax Action Handlers (Variants, ERP Stores, Autocomplete)
AJAX_ACTION_ENDPOINT = f"{VT_HOST}/AjaxAction.aspx"

# 3. Microservice Gateway Proxy & Cart Handlers
SYS_AJAX_ENDPOINT = f"{VT_HOST}/Site/_Sys/ajax.aspx"

# 4. Server-Side Async Component Renderer (Catalog & Pagination)
USER_CONTROL_ASYNC_ENDPOINT = f"{VT_HOST}/Site/_Sys/GetUserControlAsync.aspx"
USER_CONTROL_ENDPOINT = f"{VT_HOST}/Site/_Sys/GetUserControl.aspx"

# Standard HTTP Headers
HEADERS_COMMON = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": f"{VT_HOST}/",
    "Origin": VT_HOST,
}

HEADERS_AJAX = {
    **HEADERS_COMMON,
    "X-Requested-With": "XMLHttpRequest",
}

HEADERS_JSON_RPC = {
    **HEADERS_AJAX,
    "Content-Type": "application/json; charset=utf-8",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}

# Catalog Category & Manufacturer Identifiers
CATEGORIES = {
    "phone": "010001",
    "tablet": "010003",       # Máy tính bảng / iPad
    "smartwatch": "010005023", # Apple Watch
    "earphone": "010005005",   # Tai nghe / AirPods
    "pencil": "010005019",     # Apple Pencil & Phụ kiện khác
    "charger": "010005014",    # Cáp sạc Apple
    "case": "010005012",       # Bao da, ốp lưng Apple
}

APPLE_ECOSYSTEM_CATEGORIES = {
    "iPhone": "010001",
    "iPad": "010003",
    "Apple Watch": "010005023",
    "AirPods": "010005005",
    "Apple Pencil & PK": "010005019",
    "Sạc Cáp Apple": "010005014",
    "Ốp Lưng Apple": "010005012",
}

MANUFACTURERS = {
    "apple": "1",
    "samsung": "2",
    "oppo": "3",
    "xiaomi": "4",
    "vivo": "5",
    "realme": "6",
    "garmin": "145",
}

# Master Province Codes Mapping (Key regions)
KEY_PROVINCES = {
    "-1": "Toàn quốc",
    "1": "Hà Nội",
    "2": "TP. Hồ Chí Minh",
    "3": "Đà Nẵng",
    "4": "Hải Phòng",
    "5": "Cần Thơ",
}

# Pre-defined Apple Seed Links (From sites.py)
DEFAULT_SEED_PIDS = [
    "339630",  # iPhone 16 Pro Max 256GB
    "339631",  # iPhone 16 Pro Max 512GB
    "339632",  # iPhone 16 Pro Max 1TB
    "339623",  # iPhone 16 Pro 128GB
    "339614",  # iPhone 16 128GB
    "339618",  # iPhone 16 Plus 128GB
    "317053",  # iPhone 15 128GB
    "317054",  # iPhone 15 256GB
    "288660",  # iPhone 13 128GB
    "293821",  # iPhone 14 128GB
]
