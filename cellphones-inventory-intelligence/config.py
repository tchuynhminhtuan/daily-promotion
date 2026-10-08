"""
CellphoneS Inventory Intelligence - Central Configuration
=========================================================
Architectural configuration module for CellphoneS reverse-engineering,
GraphQL API Gateway endpoints, geographic routing, and master paths.
"""

from pathlib import Path

# Project paths
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

# API Gateways & Endpoints
CPS_HOST = "https://cellphones.com.vn"
API_HOST = "https://api.cellphones.com.vn"
SMEMBER_HOST = "https://api.smember.com.vn"
CUSTOMER_HOST = "https://customer.cps.onl"

GRAPHQL_V2_ENDPOINT = f"{API_HOST}/v2/graphql/query"
GRAPHQL_DASHBOARD_ENDPOINT = f"{API_HOST}/graphql-dashboard/graphql/query"
CART_V3_ENDPOINT = f"{API_HOST}/v3/cart"

# Standard HTTP Headers
HEADERS_COMMON = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": CPS_HOST,
    "Referer": f"{CPS_HOST}/",
    "Content-Type": "application/json",
}

# Company Entity Identifiers
COMPANY_CELLPHONES = 1
COMPANY_DIENTHOAIVUI = 7

# Key Geographic Province Identifiers (cps_province_id)
PROVINCE_CODES = {
    "30": "Hồ Chí Minh",
    "70": "Hà Nội",
    "17": "Đà Nẵng",
    "34": "Hải Phòng",
    "18": "Cần Thơ",
    "11": "Bình Dương",
    "24": "Đồng Nai",
}
DEFAULT_PROVINCE_ID = 30  # TP. Hồ Chí Minh

# SMember Membership Tiers
SMEMBER_TIERS = {
    "root": "Giá Niêm Yết",
    "special": "Giá Khuyến Mãi",
    "snew": "Hạng S-New",
    "smem": "Hạng S-Mem",
    "svip": "Hạng S-VIP",
}

# Stock State Mappings
STOCK_AVAILABLE_STATES = {
    46: "Có hàng sẵn tại quầy (In-Stock Physical)",
    4920: "Hàng sắp về / Đặt trước (Pre-Order / In-Transit)",
    48: "Tạm hết hàng (Out of Stock)",
}

# Reusable GraphQL Queries
QUERY_GET_PRODUCTS_BY_ARRAY_ID = """
query getProductListByArrayId(
    $province_id: Int!,
    $product_ids: [String!]!,
    $size: Int!
) {
    products(
        filter: {
            static: {
                province_id: $province_id,
                product_id: $product_ids,
                stock: {
                    from: 0
                }
            }
        },
        size: $size
    ) {
        general {
            product_id
            url_path
            name
        }
        filterable {
            stock_available_id
            company_stock_id
            is_parent
            price
            prices
            special_price
            thumbnail
            stock
            categories
            promotion_information
        }
    }
}
"""
