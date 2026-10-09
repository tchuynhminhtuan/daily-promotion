#!/usr/bin/env python3
"""
Script 01: Crawl Total Inventory for All SKUs in a Category.
Usage:
    python3 01_crawl_total_inventory.py --slug san-pham-apple --max-pages 2
    python3 01_crawl_total_inventory.py --slug laptop
"""

import os
import sys
import json
import argparse
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.pipeline.catalog_crawler import PhongVuCatalogCrawler


def main():
    parser = argparse.ArgumentParser(description="Phong Vu Total Inventory Crawler")
    parser.add_argument("--slug", type=str, default="san-pham-apple", help="Category slug (e.g. san-pham-apple, laptop)")
    parser.add_argument("--max-pages", type=int, default=None, help="Maximum pages to fetch")
    parser.add_argument("--workers", type=int, default=4, help="Concurrent workers")
    args = parser.parse_args()

    crawler = PhongVuCatalogCrawler()
    products = crawler.crawl_category(
        slug=args.slug,
        max_pages=args.max_pages,
        max_workers=args.workers
    )

    if not products:
        print("[!] Không có dữ liệu để lưu.")
        return

    # Lưu dữ liệu ra data/raw/
    output_dir = os.path.join(PROJECT_ROOT, "data", "raw")
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = os.path.join(output_dir, f"phongvu_{args.slug}_{timestamp}.json")
    latest_file = os.path.join(output_dir, f"phongvu_{args.slug}_latest.json")

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    with open(latest_file, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    print(f"\n💾 Đã lưu snapshot vào:")
    print(f"  • {out_file}")
    print(f"  • {latest_file}")

    # Báo cáo tóm tắt
    scarcity_items = [p for p in products if p.get("scarcity_flag")]
    print("\n" + "=" * 95)
    print(f"📊 BÁO CÁO TỒN KHO TỔNG PHONG VŨ - DANH MỤC: '{args.slug}' ({len(products)} SKU)")
    print("=" * 95)
    print(f"{'Mã SKU':<12} | {'Tên sản phẩm':<38} | {'Giá bán (₫)':<12} | {'Tồn kho':<12} | {'Tình trạng'}")
    print("-" * 95)

    # Hiển thị 10 sản phẩm đầu và các sản phẩm khan hiếm
    sample_display = scarcity_items[:5] + [p for p in products if not p.get("scarcity_flag")][:5]
    for p in sample_display:
        name = p.get("name", "")[:36]
        price = f"{p.get('price', 0):,}"
        qty = p.get("stock_quantity", 0)
        status = p.get("stock_status", "")
        print(f"{p.get('sku', ''):<12} | {name:<38} | {price:<12} | {qty:<12} | {status}")

    print("=" * 95)
    print(f"⚠️ Phát hiện {len(scarcity_items)} SKU đang ở trạng thái KHAN HIẾM (Tồn kho <= 5 máy)!")


if __name__ == "__main__":
    main()
