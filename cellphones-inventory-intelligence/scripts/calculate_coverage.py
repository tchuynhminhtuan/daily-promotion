#!/usr/bin/env python3
"""
Product Line Coverage Intelligence - CellphoneS
================================================
Calculates real physical showroom coverage and nationwide province coverage
for a given product line (e.g. iPhone 16, iPhone 16 Pro Max, iPad Air 6...).
"""

import argparse
import json
import logging
from pathlib import Path
import sys

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_DIR))
import config
from src.client import CPSApiClient

logging.basicConfig(level=logging.WARNING)


def calculate_line_coverage(slug_or_url: str, province_id: int = config.DEFAULT_PROVINCE_ID):
    client = CPSApiClient()

    # 1. Fetch Nuxt state to get all child color/capacity variants
    state = client.fetch_product_nuxt_state(slug_or_url)
    if not state:
        print(f"❌ Không tìm thấy thông tin sản phẩm: {slug_or_url}")
        return

    name = state.get("name")
    parent_id = state.get("productId")
    child_ids = state.get("child_product", []) or [parent_id]
    relations = state.get("productData", {}).get("general", {}).get("relation", [])

    # Master stores count for province
    master_stores_file = config.MASTER_DIR / "cps_master_stores.json"
    total_province_stores = 0
    if master_stores_file.exists():
        with open(master_stores_file, "r", encoding="utf-8") as f:
            all_master_stores = json.load(f)
        total_province_stores = len([s for s in all_master_stores if s.get("province_id") == province_id])

    province_name = config.PROVINCE_CODES.get(str(province_id), f"Tỉnh {province_id}")

    print("=" * 70)
    print(f"📱 PHÂN TÍCH ĐỘ PHỦ TỒN KHO THỰC TẾ: {name}")
    print(f"📍 Khu vực đối soát: {province_name} (Tổng mạng lưới: {total_province_stores} showroom)")
    print("=" * 70)

    # 2. Nationwide Province Coverage
    prov_stock_map = client.get_instock_provinces(child_ids)
    all_active_provinces = set()
    for pid, p_list in prov_stock_map.items():
        for p in p_list:
            all_active_provinces.add(p.get("province_id"))

    total_provinces_vn = 63
    prov_coverage_pct = (len(all_active_provinces) / total_provinces_vn * 100) if total_provinces_vn else 0

    print(f"\n🌍 1. ĐỘ PHỦ TỈNH/THÀNH TOÀN QUỐC (Nationwide Province Coverage):")
    print(f"   • Số tỉnh/thành phố còn hàng : {len(all_active_provinces)} / 63")
    print(f"   • Tỷ lệ phủ sóng toàn quốc    : {prov_coverage_pct:.1f}%")
    if not all_active_provinces:
        print(f"   🚨 CẢNH BÁO: Toàn bộ dòng sản phẩm này đã HẾT HÀNG TRÊN TOÀN QUỐC!")

    # 3. Store-level coverage in target province
    print(f"\n🏬 2. ĐỘ PHỦ SHOWROOM TẠI {province_name.upper()} (Store-Level Coverage):")
    unique_stock_shops = {}
    variant_details = []

    for cid in child_ids:
        shops_data = client.get_shops_stock(cid, province_id=province_id)
        shops_count = sum(len(d.get("shops", [])) for d in shops_data)
        variant_details.append({"id": cid, "shops_count": shops_count})

        for d in shops_data:
            for s in d.get("shops", []):
                sid = s.get("id")
                if sid not in unique_stock_shops:
                    unique_stock_shops[sid] = s

    total_active_shops = len(unique_stock_shops)
    store_coverage_pct = (total_active_shops / total_province_stores * 100) if total_province_stores > 0 else 0

    print(f"   • Số showroom có sẵn ít nhất 1 biến thể : {total_active_shops} / {total_province_stores}")
    print(f"   • Tỷ lệ phủ showroom tại khu vực       : {store_coverage_pct:.1f}%")

    if total_active_shops > 0:
        print(f"\n📍 Danh sách top showroom đang có sẵn máy:")
        for idx, (sid, s) in enumerate(list(unique_stock_shops.items())[:5], 1):
            print(f"   {idx}. {s.get('address')} (ĐT: {s.get('phone', 'N/A')})")
        if total_active_shops > 5:
            print(f"   ... và {total_active_shops - 5} showroom khác.")
    else:
        print(f"   ❌ Không có bất kỳ showroom nào tại {province_name} còn hàng.")

    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculate store coverage for a product line.")
    parser.add_argument("target", help="Product slug (e.g. iphone-16, iphone-16-pro-max)")
    parser.add_argument("--province", type=int, default=config.DEFAULT_PROVINCE_ID, help="Province ID (default: 30)")
    args = parser.parse_args()

    calculate_line_coverage(args.target, province_id=args.province)
