#!/usr/bin/env python3
"""
[03] Scan Viettel Store Apple Ecosystem & Catalog Inventory
===========================================================
Batch scans products across the Viettel Store catalog:
Supports predefined Apple product seeds and dynamic category crawls,
extracting real-time nationwide stock, ERP pricing, and store coverage.

Usage:
  python3 scripts/03_scan_catalog_inventory.py --limit 15 --concurrency 6
  python3 scripts/03_scan_catalog_inventory.py --all --concurrency 8
"""

import argparse
import logging
from pathlib import Path
import sys

# Add project root to sys.path
PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_DIR))
import config
from src.pipeline.scanner import ViettelScanner
from src.client import ViettelStoreClient

# Try importing total_links from sites.py if available
try:
    sys.path.append(str(PROJECT_DIR.parent / "src" / "crawlers"))
    # pyrefly: ignore [missing-import]
    from utils.sites import total_links
    VT_URLS_FROM_SITES = total_links.get("vt_urls", [])
except Exception:
    VT_URLS_FROM_SITES = []

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def main():
    parser = argparse.ArgumentParser(description="Scan Viettel Store inventory in batch")
    parser.add_argument("--limit", type=int, default=0, help="Maximum number of items to scan (0 = unlimited)")
    parser.add_argument("--all", action="store_true", help="Scan all available items in the selected category")
    parser.add_argument("--apple-all", action="store_true", help="Scan all items across the ENTIRE Apple ecosystem (iPhone 18/17/16, iPad, Watch, AirPods, Pencil)")
    parser.add_argument("--concurrency", type=int, default=8, help="Thread concurrency pool")
    parser.add_argument("--category", type=str, default="all", help="Category: all, iphone, ipad, watch, airpods, pencil, phone, tablet, smartwatch")
    parser.add_argument("--brand", type=str, default="apple", help="Brand: apple, samsung")
    args = parser.parse_args()

    print("=" * 80)
    print("🚀 [BƯỚC 03] QUÉT TỒN KHO HỆ THỐNG VIETTEL STORE (NATIONWIDE INVENTORY SCANNER)")
    print("=" * 80)

    target_items = []
    client = ViettelStoreClient()

    # 1. Full Apple Ecosystem Mode
    if args.apple_all or (args.brand.lower() == "apple" and args.category.lower() == "all"):
        print("🍏 Đang khám phá TOÀN BỘ Hệ sinh thái Apple (iPhone, iPad, Watch, AirPods, Pencil)...")
        target_items = client.discover_all_apple_products()
        print(f"📦 Đã tìm thấy {len(target_items)} sản phẩm Apple chính hãng trên Viettel Store!")

    # 2. Specific Category Discovery
    elif args.category and args.category.lower() != "all":
        cat_key = args.category.lower()
        cat_id = config.CATEGORIES.get(cat_key) or config.APPLE_ECOSYSTEM_CATEGORIES.get(args.category)
        if not cat_id:
            # Map aliases
            alias_map = {
                "iphone": "010001",
                "ipad": "010003",
                "watch": "010005023",
                "airpods": "010005005",
                "pencil": "010005019",
            }
            cat_id = alias_map.get(cat_key, "010001")

        man_id = config.MANUFACTURERS.get(args.brand, "1")
        print(f"🌐 Đang khám phá danh mục CatID={cat_id}, ManID={man_id}...")
        page = 1
        while True:
            items = client.get_catalog_page(cat_id=cat_id, man_id=man_id, page=page, page_size=50)
            if not items:
                break
            for it in items:
                it["category_group"] = args.category.upper()
                target_items.append(it)
            if len(items) < 50:
                break
            page += 1

    # 3. Fallback to sites.py if available and nothing found
    if not target_items and VT_URLS_FROM_SITES:
        print(f"📦 Sử dụng {len(VT_URLS_FROM_SITES)} URLs Apple Viettel từ sites.py...")
        for u in VT_URLS_FROM_SITES:
            pid = ViettelScanner.extract_pid_from_url(u)
            if pid:
                target_items.append({"product_id": pid, "url": u, "name": f"Apple Item pid{pid}", "category_group": "iPhone"})

    # Apply limits if requested
    if args.limit and args.limit > 0 and len(target_items) > args.limit:
        print(f"⚙️ Giới hạn số lượng quét: {args.limit} / {len(target_items)} sản phẩm.")
        target_items = target_items[:args.limit]

    print(f"🎯 Số lượng sản phẩm sẽ quét thực tế: {len(target_items)}")
    print(f"⚡ Số luồng đồng thời (Concurrency): {args.concurrency}")
    print("-" * 80)

    scanner = ViettelScanner(concurrency=args.concurrency)
    results = scanner.scan_catalog(target_items=target_items, include_stores=True, save_snapshot=True)

    print("\n" + "=" * 80)
    print("📊 TỔNG HỢP KẾT QUẢ QUÉT TỒN KHO:")
    total_in_stock = sum(1 for p in results if p.has_physical_stock)
    total_stock_count = sum(p.total_nationwide_stock for p in results)
    print(f"  • Tổng số sản phẩm đã quét: {len(results)}")
    print(f"  • Số sản phẩm CÒN HÀNG:     {total_in_stock} / {len(results)} ({total_in_stock / max(1, len(results)):.1%})")
    print(f"  • Tổng số lượng máy trong kho: {total_stock_count:,} máy/phụ kiện")
    print("=" * 80)


if __name__ == "__main__":
    main()
