#!/usr/bin/env python3
"""
[04] Generate Inventory Intelligence & Store Coverage Report
============================================================
Analyzes the latest snapshot data from Viettel Store, calculates store coverage,
identifies inventory concentrations, and produces high-level intelligence reports.

Usage:
  python3 scripts/04_generate_coverage_report.py
"""

from collections import Counter
import json
import logging
from pathlib import Path
import sys

# Add project root to sys.path
PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_DIR))
import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def main():
    print("=" * 80)
    print("📊 [BƯỚC 04] BÁO CÁO PHÂN TÍCH TỒN KHO & ĐỘ PHỦ SIÊU THỊ VIETTEL STORE")
    print("=" * 80)

    snapshot_file = config.SNAPSHOTS_DIR / "viettel_inventory_latest.json"
    if not snapshot_file.exists():
        print(f"❌ Chưa tìm thấy file snapshot tại {snapshot_file}. Hãy chạy bước 03 trước!")
        return

    with open(snapshot_file, "r", encoding="utf-8") as f:
        products = json.load(f)

    if not products:
        print("⚠️ File snapshot không có dữ liệu sản phẩm.")
        return

    total_products = len(products)
    in_stock_products = [p for p in products if p.get("has_physical_stock")]
    out_of_stock_products = [p for p in products if not p.get("has_physical_stock")]
    total_units = sum(p.get("total_nationwide_stock", 0) for p in products)

    # Store concentration analysis
    store_counter = Counter()
    variant_rows = []

    for p in products:
        for v in p.get("variants", []):
            variant_rows.append(v)
            for s in v.get("stores_in_stock", []):
                store_code = s.get("store_code")
                if store_code:
                    store_counter[store_code] += 1

    # Category Breakdown Analysis
    cat_stats = {}
    for p in products:
        cgroup = p.get("category_group") or p.get("category") or "Khác"
        if cgroup not in cat_stats:
            cat_stats[cgroup] = {"total": 0, "in_stock": 0, "stock_units": 0, "items": []}
        cat_stats[cgroup]["total"] += 1
        units = p.get("total_nationwide_stock", 0)
        cat_stats[cgroup]["stock_units"] += units
        if p.get("has_physical_stock"):
            cat_stats[cgroup]["in_stock"] += 1
        cat_stats[cgroup]["items"].append(p)

    print(f"\n📈 1. TỔNG QUAN CHỈ SỐ TOÀN DIỆN:")
    print(f"  • Tổng số Model sản phẩm khảo sát:  {total_products}")
    print(f"  • Số Model CÒN HÀNG trên hệ thống: {len(in_stock_products)} ({len(in_stock_products)/total_products:.1%})")
    print(f"  • Số Model HẾT HÀNG / Đặt trước:   {len(out_of_stock_products)} ({len(out_of_stock_products)/total_products:.1%})")
    print(f"  • Tổng số lượng tồn trong kho ERP: {total_units:,} chiếc/sản phẩm")
    print(f"  • Tổng số biến thể (SKU/Rules):     {len(variant_rows)}")

    print(f"\n📂 2. PHÂN BỔ TỒN KHO THEO DANH MỤC HỆ SINH THÁI APPLE:")
    print(f"{'Danh Mục':<22} | {'Tổng SKU':<10} | {'Còn Hàng':<10} | {'Tồn ERP':<12} | {'Tỷ lệ còn'}")
    print("-" * 65)
    for cgroup, stats in sorted(cat_stats.items(), key=lambda x: x[1]["stock_units"], reverse=True):
        ratio = stats["in_stock"] / max(1, stats["total"])
        print(f"{cgroup:<22} | {stats['total']:<10} | {stats['in_stock']:<10} | {stats['stock_units']:<12,}| {ratio:.1%}")

    print(f"\n🏆 3. TOP SẢN PHẨM CÓ TỒN KHO CAO NHẤT:")
    sorted_by_stock = sorted(products, key=lambda x: x.get("total_nationwide_stock", 0), reverse=True)
    print(f"{'PID':<8} | {'Danh Mục':<15} | {'Tồn Kho':<8} | {'Giá Bán':<15} | {'Tên Sản Phẩm'}")
    print("-" * 80)
    for p in sorted_by_stock[:10]:
        stock = p.get("total_nationwide_stock", 0)
        cgroup = p.get("category_group") or p.get("category") or "Khác"
        variants = p.get("variants", [])
        sell_price = variants[0].get("sell_price", 0) if variants else 0
        price_str = f"{sell_price:,.0f} đ" if sell_price else "N/A"
        name = p.get("product_name", f"PID {p.get('product_id')}")
        print(f"{p.get('product_id'):<8} | {cgroup:<15} | {stock:<8} | {price_str:<15} | {name[:32]}")

    print(f"\n🏪 4. TOP SIÊU THỊ VIETTEL CÓ MẶT HÀNG CÒN NHIỀU NHẤT:")
    print(f"{'Mã Siêu Thị':<12} | {'Số lượt SKU có hàng':<20}")
    print("-" * 35)
    for store_code, count in store_counter.most_common(10):
        print(f"{store_code:<12} | {count:<20}")

    # Generate Markdown Report File
    report_md = config.REPORTS_DIR / "viettel_inventory_intelligence_summary.md"
    with open(report_md, "w", encoding="utf-8") as f:
        f.write("# 📊 BÁO CÁO PHÂN TÍCH TỒN KHO HỆ THỐNG VIETTEL STORE TOÀN QUỐC\n\n")
        f.write(f"- **Thời gian quét:** {products[0].get('last_updated', 'N/A')}\n")
        f.write(f"- **Tổng số sản phẩm quét:** {total_products} sản phẩm thuộc toàn bộ hệ sinh thái Apple\n")
        f.write(f"- **Tỷ lệ còn hàng:** {len(in_stock_products)/total_products:.1%}\n")
        f.write(f"- **Tổng lượng tồn ERP:** {total_units:,} chiếc\n\n")

        f.write("## 1. Phân Bổ Tồn Kho Theo Danh Mục Apple\n\n")
        f.write("| Danh mục | Tổng SKU | Còn hàng | Tồn ERP (chiếc) | Tỷ lệ khả dụng |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- |\n")
        for cgroup, stats in sorted(cat_stats.items(), key=lambda x: x[1]["stock_units"], reverse=True):
            ratio = stats["in_stock"] / max(1, stats["total"])
            f.write(f"| **{cgroup}** | {stats['total']} | {stats['in_stock']} | {stats['stock_units']:,} | {ratio:.1%} |\n")

        f.write("\n## 2. Chi Tiết Tồn Kho Từng Sản Phẩm Theo Nhóm\n\n")
        for cgroup, stats in sorted(cat_stats.items(), key=lambda x: x[1]["total"], reverse=True):
            f.write(f"### Nhóm: {cgroup} ({len(stats['items'])} sản phẩm)\n\n")
            f.write("| PID | Tên sản phẩm | Tồn kho ERP | Trạng thái | Giá bán thực tế | Số siêu thị có hàng |\n")
            f.write("| :--- | :--- | :--- | :--- | :--- | :--- |\n")
            sorted_items = sorted(stats["items"], key=lambda x: x.get("total_nationwide_stock", 0), reverse=True)
            for p in sorted_items:
                status = "🟢 Còn hàng" if p.get("has_physical_stock") else "🔴 Hết hàng"
                store_cnt = sum(len(v.get("stores_in_stock", [])) for v in p.get("variants", []))
                first_var = p.get("variants", [{}])[0] if p.get("variants") else {}
                price = first_var.get("sell_price", 0)
                price_str = f"{price:,.0f} đ" if price else "Liên hệ"
                f.write(f"| [{p.get('product_id')}]({p.get('url')}) | {p.get('product_name')} | **{p.get('total_nationwide_stock')}** | {status} | {price_str} | {store_cnt} siêu thị |\n")
            f.write("\n")

    print("\n" + "=" * 80)
    print(f"📄 Báo cáo chi tiết dạng Markdown đã được tạo: {report_md}")
    print("=" * 80)


if __name__ == "__main__":
    main()
