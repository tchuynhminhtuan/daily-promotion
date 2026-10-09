#!/usr/bin/env python3
"""
Script 02: Probe Total Inventory & Details for a Single SKU.
Usage:
    python3 02_probe_sku_single.py 260901559
    python3 02_probe_sku_single.py 260900725
"""

import os
import sys
import json
import argparse

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.pipeline.sku_prober import PhongVuSkuProber


def main():
    parser = argparse.ArgumentParser(description="Phong Vu Single SKU Prober")
    parser.add_argument("sku", type=str, nargs="?", default="260901559", help="Phong Vu product SKU")
    args = parser.parse_args()

    prober = PhongVuSkuProber()
    print(f"\n🔎 Đang truy vấn SKU: {args.sku} trên hệ thống Phong Vũ...")
    res = prober.probe_sku(args.sku)

    if not res:
        print(f"❌ Không tìm thấy thông tin cho SKU: {args.sku}")
        return

    print("=" * 70)
    print("📦 THÔNG TIN TỒN KHO & CHI TIẾT SẢN PHẨM PHONG VŨ")
    print("=" * 70)
    print(f"• Mã SKU               : {res.get('sku')}")
    print(f"• Tên sản phẩm         : {res.get('name')}")
    print(f"• Thương hiệu          : {res.get('brand')}")
    print(f"• Giá bán hiện tại     : {res.get('price', 0):,} ₫")
    print(f"• Giá niêm yết         : {res.get('supplier_retail_price', 0):,} ₫")
    print(f"• Giảm giá             : {res.get('discount_percent')}")
    print(f"• Trạng thái kinh doanh: {'ĐANG MỞ BÁN' if res.get('sellable') else 'NGỪNG BÁN'}")
    print(f"• Tồn kho khả dụng     : {res.get('total_available')}")
    print(f"• Đánh giá tồn kho     : {res.get('stock_status_summary')}")
    print("=" * 70)


if __name__ == "__main__":
    main()
