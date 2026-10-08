#!/usr/bin/env python3
"""
FPT Macro Inventory Delta Analysis Engine
==========================================
So sánh 2 snapshot tồn kho theo mốc thời gian để nghiên cứu biến động:
1. 📉 Giảm tồn kho (Delta < 0): Lượng máy BÁN RA (Sales Outflow) & Doanh thu ước tính.
2. 📈 Tăng tồn kho (Delta > 0): Lượng máy NHẬP THÊM (Restock Inflow - kho tổng nhập hàng).
3. ⏸️ Đứng im (Delta == 0): Lượng máy tồn đọng / chậm luân chuyển.

Hỗ trợ:
- Tự động so sánh 2 snapshot mới nhất trong data/snapshots/
- Hoặc người dùng chỉ định 2 file snapshot bất kỳ qua dòng lệnh
"""

import os
import sys
import glob
import json
import argparse
from datetime import datetime
from typing import Dict, Any, List, Tuple

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

SNAPSHOT_DIR = os.path.join(PROJECT_ROOT, "data", "snapshots")
REPORTS_DIR = os.path.join(PROJECT_ROOT, "data", "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


def find_latest_two_snapshots() -> Tuple[str, str]:
    files = glob.glob(os.path.join(SNAPSHOT_DIR, "fast_20*.json"))
    files.sort(key=os.path.getmtime)
    if len(files) < 2:
        return None, None
    return files[-2], files[-1]


def load_snapshot(filepath: str) -> Dict[str, Any]:
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def analyze_delta(prev_file: str, curr_file: str):
    data_prev = load_snapshot(prev_file)
    data_curr = load_snapshot(curr_file)

    time_prev = data_prev.get("recorded_at") or data_prev.get("timestamp", "Trước")
    time_curr = data_curr.get("recorded_at") or data_curr.get("timestamp", "Hiện tại")

    prev_items = {p["sku"]: p for p in data_prev.get("products", [])}
    curr_items = {p["sku"]: p for p in data_curr.get("products", [])}

    all_skus = set(prev_items.keys()) | set(curr_items.keys())

    sold_items = []      # Delta < 0
    restocked_items = [] # Delta > 0
    unchanged_items = [] # Delta == 0

    category_summary = {}

    for sku in all_skus:
        p_prev = prev_items.get(sku, {})
        p_curr = curr_items.get(sku, {})

        q_prev = p_prev.get("qty", 0)
        q_curr = p_curr.get("qty", 0)
        delta = q_curr - q_prev

        name = p_curr.get("name") or p_prev.get("name", "N/A")
        cat = p_curr.get("category") or p_prev.get("category", "Khác")
        price = p_curr.get("price") or p_prev.get("price", 0)

        if cat not in category_summary:
            category_summary[cat] = {"sold_units": 0, "sold_revenue": 0, "restocked_units": 0}

        record = {
            "sku": sku,
            "name": name,
            "category": cat,
            "price": price,
            "q_prev": q_prev,
            "q_curr": q_curr,
            "delta": delta
        }

        if delta < 0:
            sold_qty = abs(delta)
            est_rev = sold_qty * price
            record["sold_qty"] = sold_qty
            record["est_revenue"] = est_rev
            sold_items.append(record)
            category_summary[cat]["sold_units"] += sold_qty
            category_summary[cat]["sold_revenue"] += est_rev
        elif delta > 0:
            record["restock_qty"] = delta
            restocked_items.append(record)
            category_summary[cat]["restocked_units"] += delta
        else:
            unchanged_items.append(record)

    # Sắp xếp
    sold_items.sort(key=lambda x: x["est_revenue"], reverse=True)
    restocked_items.sort(key=lambda x: x["restock_qty"], reverse=True)

    total_sold_units = sum(i["sold_qty"] for i in sold_items)
    total_sold_rev = sum(i["est_revenue"] for i in sold_items)
    total_restocked_units = sum(i["restock_qty"] for i in restocked_items)

    # In kết quả ra Console
    print("=" * 85)
    print("📊 BÁO CÁO PHÂN TÍCH BIẾN ĐỘNG TỒN KHO FPT RETAIL (DELTA INTELLIGENCE)")
    print(f"⏱️  Mốc trước: {time_prev} ({os.path.basename(prev_file)})")
    print(f"⏱️  Mốc sau:   {time_curr} ({os.path.basename(curr_file)})")
    print("=" * 85)

    print("\n📦 TỔNG QUAN THỊ TRƯỜNG TOÀN QUỐC:")
    print(f"  • Tổng máy BÁN RA ước tính:  🔥 {total_sold_units:6,d} máy | Ước tính doanh thu: ~{total_sold_rev/1e9:,.2f} tỷ VNĐ")
    print(f"  • Tổng máy NHẬP KHO (bơm hàng): 📥 {total_restocked_units:6,d} máy")
    print(f"  • Biến thể có giao dịch:       {len(sold_items) + len(restocked_items)}/{len(all_skus)} SKU")

    print("\n🏢 BIẾN ĐỘNG THEO DANH MỤC SẢN PHẨM:")
    print(f"  {'Danh Mục':<15} | {'Bán Ra (Máy)':<15} | {'Doanh Thu Ước Tính':<22} | {'Nhập Hàng (Máy)':<15}")
    print("  " + "-" * 73)
    for cat, stats in category_summary.items():
        rev_str = f"~{stats['sold_revenue']/1e9:,.2f} tỷ đ" if stats['sold_revenue'] > 0 else "0 đ"
        print(f"  {cat:<15} | {stats['sold_units']:>12,d} máy | {rev_str:>20} | {stats['restocked_units']:>12,d} máy")

    if sold_items:
        print("\n🔥 TOP 10 SẢN PHẨM BÁN CHẠY NHẤT (THEO GIÁ TRỊ DOANH SỐ):")
        print(f"  {'#':<3} {'Tên sản phẩm':<40} | {'Đã Bán':<8} | {'Tồn Còn':<8} | {'Doanh Thu':<15}")
        print("  " + "-" * 80)
        for idx, item in enumerate(sold_items[:10], 1):
            rev_fmt = f"{item['est_revenue']/1e6:,.1f} tr đ"
            print(f"  {idx:<3} {item['name'][:40]:<40} | {item['sold_qty']:>6d} | {item['q_curr']:>6d} | {rev_fmt:>13}")

    if restocked_items:
        print("\n📥 TOP LÔ HÀNG VỪA ĐƯỢC NHẬP THÊM VÀO KHO (RESTOCKED):")
        print(f"  {'#':<3} {'Tên sản phẩm':<40} | {'Nhập Thêm':<10} | {'Tồn Mới':<8}")
        print("  " + "-" * 65)
        for idx, item in enumerate(restocked_items[:10], 1):
            print(f"  {idx:<3} {item['name'][:40]:<40} | +{item['restock_qty']:>8d} | {item['q_curr']:>6d}")

    # Xuất báo cáo Markdown
    report_md_path = os.path.join(REPORTS_DIR, "inventory_delta_latest.md")
    report_json_path = os.path.join(REPORTS_DIR, "inventory_delta_latest.json")

    with open(report_md_path, "w", encoding="utf-8") as f:
        f.write("# 📊 Báo Cáo Biến Động Tồn Kho FPT Retail (Delta Intelligence)\n\n")
        f.write(f"- **Mốc đo 1 (Trước)**: `{time_prev}`\n")
        f.write(f"- **Mốc đo 2 (Hiện tại)**: `{time_curr}`\n")
        f.write(f"- **Thời gian phân tích**: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n\n")

        f.write("## 1. Tổng Quan Toàn Hệ Thống\n\n")
        f.write(f"| Chỉ Số | Giá Trị |\n| :--- | :--- |\n")
        f.write(f"| **Tổng lượng máy bán ra** | **{total_sold_units:,} máy** |\n")
        f.write(f"| **Doanh thu bán ra ước tính** | **~{total_sold_rev/1e9:,.2f} tỷ VNĐ** |\n")
        f.write(f"| **Tổng lượng máy nhập thêm kho** | **+{total_restocked_units:,} máy** |\n\n")

        f.write("## 2. Biến Động Theo Ngành Hàng\n\n")
        f.write("| Ngành Hàng | Máy Bán Ra | Doanh Thu Ước Tính | Máy Nhập Kho |\n| :--- | :---: | :---: | :---: |\n")
        for cat, stats in category_summary.items():
            f.write(f"| **{cat}** | {stats['sold_units']:,} | ~{stats['sold_revenue']/1e9:,.2f} tỷ đ | +{stats['restocked_units']:,} |\n")

        if sold_items:
            f.write("\n## 3. Top Sản Phẩm Bán Chạy Nhất\n\n")
            f.write("| # | Tên Sản Phẩm | SKU | Đã Bán | Tồn Hiện Tại | Giá Trị Bán Ra |\n| :---: | :--- | :---: | :---: | :---: | :---: |\n")
            for idx, item in enumerate(sold_items[:15], 1):
                f.write(f"| {idx} | {item['name']} | `{item['sku']}` | **{item['sold_qty']}** | {item['q_curr']} | {item['est_revenue']/1e6:,.1f} tr đ |\n")

        if restocked_items:
            f.write("\n## 4. Top Sản Phẩm Được Bổ Sung Tồn Kho (Restock)\n\n")
            f.write("| # | Tên Sản Phẩm | SKU | Nhập Thêm | Tồn Hiện Tại |\n| :---: | :--- | :---: | :---: | :---: |\n")
            for idx, item in enumerate(restocked_items[:15], 1):
                f.write(f"| {idx} | {item['name']} | `{item['sku']}` | **+{item['restock_qty']}** | {item['q_curr']} |\n")

    # Xuất JSON
    report_data = {
        "time_prev": time_prev,
        "time_curr": time_curr,
        "total_sold_units": total_sold_units,
        "total_sold_revenue": total_sold_rev,
        "total_restocked_units": total_restocked_units,
        "category_summary": category_summary,
        "top_sold": sold_items[:20],
        "top_restocked": restocked_items[:20]
    }
    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)

    print(f"\n📑 Đã xuất báo cáo chi tiết:")
    print(f"   • Markdown: {report_md_path}")
    print(f"   • JSON:     {report_json_path}")
    print("=" * 85)


def main():
    parser = argparse.ArgumentParser(description="FPT Inventory Delta Intelligence Analyzer")
    parser.add_argument("--prev", "-p", type=str, help="Đường dẫn file snapshot trước")
    parser.add_argument("--curr", "-c", type=str, help="Đường dẫn file snapshot sau")
    args = parser.parse_args()

    prev_file = args.prev
    curr_file = args.curr

    if not prev_file or not curr_file:
        prev_file, curr_file = find_latest_two_snapshots()
        if not prev_file or not curr_file:
            print("⚠️ Chưa có đủ ít nhất 2 snapshot trong thư mục data/snapshots/ để so sánh.")
            print("💡 Hãy chạy 'python3 scripts/automation/auto_macro_snapshot.py' thêm ít nhất 1 lần nữa!")
            return

    analyze_delta(prev_file, curr_file)


if __name__ == "__main__":
    main()
