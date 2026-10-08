#!/usr/bin/env python3
"""
[02] Deep Probe Single Product Inventory & Store Breakdown
==========================================================
Investigates a specific product on Viettel Store:
Extracts all color variants, queries ASMX for real-time stock and ERP price,
and probes all physical supermarkets currently in stock.

Usage:
  python3 scripts/02_probe_product_inventory.py --pid 339614
  python3 scripts/02_probe_product_inventory.py --url https://viettelstore.vn/dien-thoai/iphone-16-pro-max-pid339630.html
"""

import argparse
import json
import logging
from pathlib import Path
import re
import sys

# Add project root to sys.path
PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_DIR))
import config
from src.client import ViettelStoreClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def main():
    parser = argparse.ArgumentParser(description="Probe single Viettel Store product inventory")
    parser.add_argument("--pid", type=str, default="339614", help="Product ID (e.g. 339614 or 339630)")
    parser.add_argument("--url", type=str, default="", help="Product URL")
    args = parser.parse_args()

    pid = args.pid
    if args.url:
        match = re.search(r"pid(\d+)", args.url, re.I)
        if match:
            pid = match.group(1)

    print("=" * 80)
    print(f"🔍 [BƯỚC 02] BẮT ĐẦU DÒ TỒN KHO THỰC TẾ VIETTEL STORE - PID: {pid}")
    print("=" * 80)

    client = ViettelStoreClient()
    product_info = client.probe_product(product_id=pid, include_stores=True)

    print(f"\n📦 KẾT QUẢ DÒ TỒN KHO CHO SẢN PHẨM PID: {product_info.product_id}")
    print(f"🌐 URL: {product_info.url}")
    print(f"📊 Tổng tồn kho toàn quốc (Amount In Stock): {product_info.total_nationwide_stock} máy")
    print(f"📍 Có hàng thực tế tại siêu thị: {'CÓ' if product_info.has_physical_stock else 'HẾT HÀNG'}")
    print("-" * 80)

    for i, v in enumerate(product_info.variants, 1):
        print(f"\n[{i}] Màu sắc / Biến thể: {v.color_name.upper()}")
        print(f"    - Mã Rule ID:       {v.rule_id}")
        print(f"    - Mã ERP SKU:       {v.erp_product_id}")
        print(f"    - Mã Spec Code:     {v.spec_code}")
        print(f"    - Giá niêm yết:     {v.price:,.0f} đ" if v.price else "    - Giá niêm yết:     N/A")
        print(f"    - Giá bán thực tế:  {v.sell_price:,.0f} đ" if v.sell_price else "    - Giá bán thực tế:  N/A")
        print(f"    - Tồn kho biến thể: {v.amount_in_stock} máy ({'Còn hàng' if v.amount_in_stock > 0 else 'Hết hàng'})")
        print(f"    - Số siêu thị có:   {len(v.stores_in_stock)} shop")

        if v.stores_in_stock:
            print("    - Danh sách siêu thị tiêu biểu:")
            for s in v.stores_in_stock[:5]:
                print(f"       * [{s.store_code}] {s.address}")
            if len(v.stores_in_stock) > 5:
                print(f"       * ... và {len(v.stores_in_stock) - 5} siêu thị khác trên toàn quốc.")

    out_file = config.SNAPSHOTS_DIR / f"probe_pid_{pid}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(product_info.to_dict(), f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 80)
    print(f"✅ Hoàn tất deep probe! Dữ liệu snapshot đã lưu tại: {out_file}")
    print("=" * 80)


if __name__ == "__main__":
    main()
