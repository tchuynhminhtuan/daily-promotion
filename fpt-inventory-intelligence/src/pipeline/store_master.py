"""
FPT Master Store Registry & Geospatial Directory Engine
Quản lý sổ bộ 602 siêu thị FPT Shop & F.Studio by FPT toàn quốc:
- Lưu trữ tọa độ GPS (Lat/Long) phục vụ bản đồ nhiệt.
- Lưu giữ cả địa chỉ mới sau sáp nhập và địa chỉ cũ trước sáp nhập (oldDisplayAddress).
- Cung cấp cơ chế tìm kiếm, tra cứu và khớp nối cửa hàng chính xác cao.
"""

import os
import sys
import json
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List, Optional

import requests

# Thêm PROJECT_ROOT vào sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import (
    MASTER_STORES_FILE,
    SHOPS_API_URL,
    HEADERS_FPTSHOP,
    ACTIVE_PROVINCES
)


def remove_accents(input_str: str) -> str:
    """Loại bỏ dấu tiếng Việt để phục vụ so sánh chuỗi không dấu."""
    if not input_str:
        return ""
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).replace('đ', 'd').replace('Đ', 'D')


def clean_address_text(addr: str) -> str:
    """Chuẩn hóa địa chỉ: bỏ dấu, viết thường, loại bỏ ký tự rác."""
    if not addr:
        return ""
    addr_no_accents = remove_accents(addr.lower())
    addr_clean = re.sub(r'[\,\.\-\/\(\)]', ' ', addr_no_accents)
    return re.sub(r'\s+', ' ', addr_clean).strip()


class FPTStoreMasterRegistry:
    """Sổ cái toàn bộ mạng lưới phân phối FPT Shop & F.Studio."""

    def __init__(self, cache_file: str = MASTER_STORES_FILE, auto_fetch: bool = True):
        self.cache_file = cache_file
        self.stores_by_code: Dict[str, Dict[str, Any]] = {}
        self.stores_list: List[Dict[str, Any]] = []

        if os.path.exists(self.cache_file):
            self.load_cache()
        elif auto_fetch:
            print("📦 Chưa có cache Master Stores FPT. Đang tải từ FPT Gateway API...")
            self.refresh_master_stores()

    def load_cache(self):
        """Đọc danh bạ siêu thị từ file JSON đã cache."""
        with open(self.cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.stores_list = data if isinstance(data, list) else data.get("stores", [])
            self.stores_by_code = {}
            for s in self.stores_list:
                if "shopCode" in s and s["shopCode"]:
                    self.stores_by_code[str(s["shopCode"])] = s
                if "store_code" in s and s["store_code"]:
                    self.stores_by_code[str(s["store_code"])] = s
        print(f"🏢 Đã nạp {len(self.stores_list)} siêu thị FPT từ cache ({self.cache_file})")

    def refresh_master_stores(self, max_workers: int = 15) -> List[Dict[str, Any]]:
        """Quét toàn bộ 34 mã tỉnh thành để thu thập trọn vẹn 602 siêu thị FPT có tọa độ GPS."""
        print(f"🔄 Đang kết nối FPT Gateway API ({SHOPS_API_URL}) cho 34 mã tỉnh...")
        all_unique_shops: Dict[str, Dict[str, Any]] = {}

        def fetch_province(p_code: str):
            try:
                resp = requests.get(
                    SHOPS_API_URL,
                    headers=HEADERS_FPTSHOP,
                    params={"provinceCode": p_code},
                    timeout=8
                )
                if resp.status_code == 200:
                    return p_code, resp.json().get("data", [])
            except Exception as e:
                print(f"⚠️ Lỗi tải tỉnh {p_code}: {e}")
            return p_code, []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(fetch_province, ACTIVE_PROVINCES))

        for p_code, shops in results:
            for s in shops:
                sc = str(s.get("shopCode", "")).strip()
                if not sc:
                    continue
                if sc not in all_unique_shops:
                    # Làm giàu nhãn nhận diện chuỗi
                    features = s.get("shopFeatures", [])
                    is_fstudio = any(f.get("code") == "12" or "fstudio" in f.get("name", "").lower() for f in features)
                    is_fstudio = is_fstudio or "fstudio" in s.get("shopName", "").lower()
                    
                    loc = s.get("location", {})
                    lat = loc.get("latitude") if isinstance(loc, dict) else None
                    lng = loc.get("longitude") if isinstance(loc, dict) else None

                    enriched_store = {
                        "shopCode": sc,
                        "shopName": s.get("shopName", ""),
                        "channel": "F.Studio by FPT" if is_fstudio else "FPT Shop",
                        "displayAddress": s.get("displayAddress", ""),
                        "legacyAddress": s.get("legacyAddress") or s.get("oldDisplayAddress", ""),
                        "provinceCode": s.get("provinceCode", p_code),
                        "latitude": lat,
                        "longitude": lng,
                        "timeOpen": s.get("timeOpen", "08:00:00"),
                        "timeClose": s.get("timeClose", "22:00:00"),
                        "phone": s.get("phone", "1800 6601"),
                        "shopFeatures": features
                    }
                    all_unique_shops[sc] = enriched_store

        self.stores_list = list(all_unique_shops.values())
        self.stores_by_code = all_unique_shops

        # Ghi ra cache JSON
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(self.stores_list, f, ensure_ascii=False, indent=2)

        print(f"✅ Đã thu thập và lưu thành công {len(self.stores_list)} siêu thị FPT vào {self.cache_file}!")
        return self.stores_list

    def get_by_code(self, shop_code: str) -> Optional[Dict[str, Any]]:
        """Lấy thông tin siêu thị theo Shop Code."""
        return self.stores_by_code.get(str(shop_code).strip())

    def search_by_query(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Tìm kiếm siêu thị theo tên đường, quận huyện hoặc mã shop."""
        q_clean = clean_address_text(query)
        results = []
        for s in self.stores_list:
            sc = str(s.get("shopCode", "")).strip()
            tree_sc = str(s.get("store_code", "")).strip()
            name_clean = clean_address_text(s.get("shopName", ""))
            tree_name_clean = clean_address_text(s.get("store_name", ""))
            addr_clean = clean_address_text(s.get("displayAddress", ""))
            old_addr_clean = clean_address_text(s.get("legacyAddress", ""))

            if (q_clean == sc or q_clean == tree_sc or 
                q_clean in name_clean or q_clean in tree_name_clean or 
                q_clean in addr_clean or q_clean in old_addr_clean):
                results.append(s)
                if len(results) >= limit:
                    break
        return results


if __name__ == "__main__":
    registry = FPTStoreMasterRegistry(auto_fetch=True)
    print(f"Tổng số shop nạp được: {len(registry.stores_list)}")
    sample = registry.get_by_code("30878")
    if sample:
        print("Mẫu shop 30878:")
        print(json.dumps(sample, indent=2, ensure_ascii=False))
