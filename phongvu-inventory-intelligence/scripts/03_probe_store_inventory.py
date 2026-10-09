#!/usr/bin/env python3
"""
Script 03: Probe Physical Inventory for a SKU Across Phong Vu Stores
Using Binary Search Cart Probing Technique O(log N).
Usage:
    python3 03_probe_store_inventory.py --sku 260901559 --store PV_HCM_01
    python3 03_probe_store_inventory.py --sku 260901559 --province "Hồ Chí Minh"
"""

import os
import sys
import json
import argparse

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.pipeline.sku_prober import PhongVuSkuProber
from src.pipeline.store_cart_prober import PhongVuStoreCartProber
from src.store_registry import PhongVuStoreRegistry


def main():
    parser = argparse.ArgumentParser(description="Phong Vu Store-Level Inventory Prober")
    parser.add_argument("--sku", type=str, default="260901559", help="Target SKU")
    parser.add_argument("--store", type=str, default=None, help="Specific Store ID (e.g. PV_HCM_01, PV_HN_01)")
    parser.add_argument("--province", type=str, default=None, help="Filter by Province name (e.g. 'Hà Nội', 'Hồ Chí Minh')")
    parser.add_argument("--upper-bound", type=int, default=50, help="Initial upper bound for binary search")
    args = parser.parse_args()

    # 1. Lấy thông tin cơ bản của SKU
    sku_prober = PhongVuSkuProber()
    sku_info = sku_prober.probe_sku(args.sku)
    product_name = sku_info.get("name", "") if sku_info else f"SKU {args.sku}"

    print("=" * 80)
    print("🎯 PHONG VŨ STORE-LEVEL INVENTORY PROBER (BINARY SEARCH CART ENGINE)")
    print("=" * 80)
    print(f"📦 SKU Mục Tiêu : {args.sku}")
    print(f"🏷️ Tên Sản Phẩm : {product_name}")
    if sku_info:
        print(f"💰 Giá Bán      : {sku_info.get('price', 0):,} ₫")
        print(f"📊 Đánh Giá Tồn : {sku_info.get('stock_status_summary')}")
    print("=" * 80)

    cart_prober = PhongVuStoreCartProber()

    # 2. Chế độ kiểm tra 1 cửa hàng cụ thể hoặc nhiều cửa hàng
    if args.store:
        res = cart_prober.probe_store_exact_stock(
            sku=args.sku,
            store_id=args.store,
            product_name=product_name,
            max_upper_bound=args.upper_bound,
            verbose=True
        )
        print("\n" + "=" * 80)
        print(f"🏁 TỔNG KẾT: Showroom {res.store_name} ({res.province})")
        print(f"   • Tồn kho máy vật lý : {res.exact_physical_stock} máy")
        print(f"   • Số bước dò         : {res.probe_steps} bước")
        print(f"   • Thời gian thực thi : {res.probe_duration_sec}s")
        print("=" * 80)
    else:
        provinces = [args.province] if args.province else None
        results = cart_prober.probe_all_stores_for_sku(
            sku=args.sku,
            product_name=product_name,
            target_provinces=provinces
        )

        print("\n" + "=" * 90)
        print(f"📊 BẢNG TỒN KHO VẬT LÝ THEO SHOWROOM - SKU: {args.sku}")
        print("=" * 90)
        print(f"{'Mã Showroom':<12} | {'Tên Showroom':<30} | {'Tỉnh/Thành':<15} | {'Tồn kho':<10} | {'Thời gian'}")
        print("-" * 90)
        for r in results:
            stock_str = f"{r.exact_physical_stock} máy" if r.in_stock_confirmed else "Hết hàng"
            print(f"{r.store_id:<12} | {r.store_name[:28]:<30} | {r.province:<15} | {stock_str:<10} | {r.probe_duration_sec}s")
        print("=" * 90)


if __name__ == "__main__":
    main()
