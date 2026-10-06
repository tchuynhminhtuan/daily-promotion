#!/usr/bin/env python3
"""
Phân tích dữ liệu tồn kho & so sánh hệ thống cũ vs hệ thống lai
"""

import sys
import pandas as pd
from typing import Dict, Any

def analyze(csv_path: str):
    print("=" * 70)
    print("📊 BÁO CÁO PHÂN TÍCH DỮ LIỆU TỒN KHO HỆ THỐNG LAI THẾ GIỚI DI ĐỘNG")
    print("=" * 70)

    df = pd.read_csv(csv_path, sep=";")
    print(f"📁 Tệp dữ liệu: {csv_path}")
    print(f"📈 Tổng số bản ghi (biến thể sản phẩm): {len(df)}")
    print(f"📦 Số sản phẩm còn hàng tại siêu thị: {len(df[df['Store_Count'] > 0])} ({len(df[df['Store_Count'] > 0])*100//len(df)}%)")
    print(f"🚫 Số sản phẩm hết hàng toàn quốc:    {len(df[df['Store_Count'] == 0])} ({len(df[df['Store_Count'] == 0])*100//len(df)}%)")

    print("\n" + "-" * 70)
    print("1. THỐNG KÊ THEO TỪNG DANH MỤC")
    print("-" * 70)
    cat_summary = df.groupby('Category').agg(
        Total_Variants=('Product_Name', 'count'),
        In_Stock_Variants=('Store_Count', lambda x: (x > 0).sum()),
        Avg_Store_Count=('Store_Count', 'mean'),
        Max_Store_Count=('Store_Count', 'max')
    ).reset_index()
    print(cat_summary.to_string(index=False))

    print("\n" + "-" * 70)
    print("2. TOP 10 SẢN PHẨM CÒN TỒN KHO NHIỀU NHẤT TRÊN TOÀN QUỐC")
    print("-" * 70)
    price_col = 'Gia_Khuyen_Mai' if 'Gia_Khuyen_Mai' in df.columns else 'Price'
    top_stock = df.sort_values(by='Store_Count', ascending=False).head(10)
    for idx, (_, r) in enumerate(top_stock.iterrows(), 1):
        price_val = r.get(price_col, 0)
        price_str = f"{int(price_val):,} đ" if pd.notnull(price_val) and price_val > 0 else "N/A"
        print(f"  {idx:2d}. {r['Product_Name']} | Màu: {r['Color']:<16} | Giá: {price_str}")
        print(f"      🏪 {r['Store_Count']} shop toàn quốc (TP.HCM: {r.get('Store_HCM', 0)}, Hà Nội: {r.get('Store_Hanoi', 0)})")

    print("\n" + "-" * 70)
    print("3. CÁC DÒNG MÁY ĐANG HẾT HÀNG TẠI TẤT CẢ SIÊU THỊ (Cháy hàng / Chưa mở bán)")
    print("-" * 70)
    out_of_stock = df[df['Store_Count'] == 0].drop_duplicates(subset=['Product_Name']).head(8)
    for idx, (_, r) in enumerate(out_of_stock.iterrows(), 1):
        price_val = r.get(price_col, 0)
        price_str = f"{int(price_val):,} đ" if pd.notnull(price_val) and price_val > 0 else "Chưa có giá chính thức"
        print(f"  ❌ {r['Product_Name']} ({r['Category']}) | Giá: {price_str}")

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "data/hybrid/tgdd_inventory_2026-10-06.csv"
    analyze(path)
