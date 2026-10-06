#!/usr/bin/env python3
"""
Deep EDA & Business Intelligence on TGDD Apple Inventory Dataset
"""

import json
import pandas as pd
import numpy as np

def run_eda(json_path: str):
    with open(json_path, encoding='utf-8') as f:
        payload = json.load(f)

    meta = payload['metadata']
    items = payload['data']
    df = pd.DataFrame(items)

    print("=" * 80)
    print("🔬 BÁO CÁO PHÂN TÍCH KHÁM PHÁ DỮ LIỆU (EDA) & BUSINESS INSIGHTS")
    print(f"Nguồn: {meta['source']} | Ngày quét: {meta['crawl_date']}")
    print("=" * 80)

    # 1. TỔNG QUAN HÀNG HÓA & GIÁ TRỊ VỐN TỒN KHO TỐI THIỂU (MINIMUM ON-SHELF CAPITAL)
    df['Min_Capital_Value'] = df['Store_Count'] * df['Gia_Khuyen_Mai']
    total_min_capital = df['Min_Capital_Value'].sum()
    
    print("\n[PHẦN 1] BỨC TRANH TỔNG THỂ & QUY MÔ VỐN TỒN KHO TRÊN KỆ")
    print("-" * 80)
    print(f"• Tổng số biến thể SKU: {len(df)}")
    print(f"• Tỷ lệ sẵn hàng (In-Stock Rate): {meta['in_stock_variants_count']}/{len(df)} ({meta['in_stock_variants_count']*100/len(df):.1f}%)")
    print(f"• Tỷ lệ hết hàng toàn quốc (Stock-Out Rate): {meta['out_of_stock_variants_count']}/{len(df)} ({meta['out_of_stock_variants_count']*100/len(df):.1f}%)")
    print(f"• Ước tính giá trị hàng hóa tối thiểu đang nằm trên kệ toàn quốc: {total_min_capital / 1e9:,.1f} TỶ VNĐ")
    print("  (Giả định mỗi shop còn hàng chỉ lưu tối thiểu đúng 1 máy)")

    # 2. PHÂN TÍCH THEO DANH MỤC (CATEGORY DEEP DIVE)
    print("\n[PHẦN 2] HIỆU NĂNG TỒN KHO & DẢI GIÁ THEO DANH MỤC")
    print("-" * 80)
    cat_grp = df.groupby('Category').agg(
        Total_SKU=('SKU', 'count'),
        In_Stock=('Store_Count', lambda x: (x > 0).sum()),
        In_Stock_Pct=('Store_Count', lambda x: f"{(x > 0).mean()*100:.1f}%"),
        Avg_Shops=('Store_Count', 'mean'),
        Median_Price=('Gia_Khuyen_Mai', 'median'),
        Total_Capital_Bil=('Min_Capital_Value', lambda x: round(x.sum() / 1e9, 1))
    ).reset_index()
    print(cat_grp.to_string(index=False))

    # 3. ĐỊA LÝ: SỰ CHÊNH LỆCH BẮC - NAM VÀ CÁC VÙNG TRỌNG ĐIỂM
    total_stores_all = df['Store_Count'].sum()
    total_hcm = df['Store_HCM'].sum()
    total_hn = df['Store_Hanoi'].sum()
    total_other = total_stores_all - (total_hcm + total_hn)

    print("\n[PHẦN 3] BẢN ĐỒ PHÂN BỔ ĐỊA LÝ HÀNG HÓA (GEOGRAPHICAL ALLOCATION)")
    print("-" * 80)
    print(f"• Tổng lượt tồn kho ghi nhận trên các shop: {total_stores_all:,} lượt sản phẩm")
    print(f"  + TP. Hồ Chí Minh: {total_hcm:,} ({total_hcm*100/total_stores_all:.1f}%)")
    print(f"  + TP. Hà Nội:      {total_hn:,} ({total_hn*100/total_stores_all:.1f}%)")
    print(f"  + 61 tỉnh thành còn lại: {total_other:,} ({total_other*100/total_stores_all:.1f}%)")
    print("=> Tỷ lệ tồn kho TP.HCM gấp ~2 lần Hà Nội, cho thấy sức mua và dung lượng thị trường miền Nam vượt trội.")

    # Top các tỉnh thành ngoài HN & HCM có hàng nhiều nhất
    all_provinces = {}
    for item in items:
        for prov, count in item.get('Province_Breakdown', {}).items():
            all_provinces[prov] = all_provinces.get(prov, 0) + count
    prov_df = pd.Series(all_provinces).sort_values(ascending=False).reset_index()
    prov_df.columns = ['Tỉnh/Thành', 'Tổng lượt tồn kho']
    print("\n• TOP 7 TỈNH/THÀNH DỒN HÀNG APPLE NHIỀU NHẤT NGOÀI HN & HCM:")
    print(prov_df[~prov_df['Tỉnh/Thành'].isin(['Thành phố Hồ Chí Minh', 'Thành phố Hà Nội'])].head(7).to_string(index=False))

    # 4. CHIẾN LƯỢC MÀU SẮC (COLOR STRATEGY & COLOR SKEW)
    print("\n[PHẦN 4] BẤT ĐỐI XỨNG MÀU SẮC TRÊN CÙNG DÒNG MÁY (COLOR SKEW)")
    print("-" * 80)
    for model in ['iPhone 17 Pro Max 256GB', 'iPhone 17 256GB', 'iPad A16 WiFi 128GB']:
        m_df = df[df['Product_Name'].str.contains(model, case=False, na=False)]
        if not m_df.empty:
            print(f"• {model}:")
            for _, r in m_df.iterrows():
                print(f"   - Màu {r['Color']:<16}: Còn tại {r['Store_Count']:3d} shop | Máy demo: {r.get('Sample_Display_Total', 0)}")

    # 5. CHIẾN LƯỢC MÁY TRƯNG BÀY (DEMO UNITS / EXPERIENCE HUBS)
    print("\n[PHẦN 5] PHÂN TÍCH ĐẦU TƯ BÀN TRẢI NGHIỆM (DEMO COUNTERS)")
    print("-" * 80)
    demo_df = df[df['Sample_Display_Total'] > 0][['Product_Name', 'Color', 'Sample_Display_Total', 'Store_Count', 'Gia_Khuyen_Mai']]
    print(demo_df.to_string(index=False))

    # 6. NHỮNG MẶT HÀNG TỒN ĐỌNG "TIỀN NẰM CHẾT" NHIỀU NHẤT
    print("\n[PHẦN 6] TOP 5 MÃ HÀNG GIỮ VỐN NHIỀU NHẤT TRÊN KỆ (CAPITAL ALLOCATION)")
    print("-" * 80)
    top_cap = df.sort_values(by='Min_Capital_Value', ascending=False).head(5)
    for idx, (_, r) in enumerate(top_cap.iterrows(), 1):
        cap_bil = r['Min_Capital_Value'] / 1e9
        print(f"  {idx}. {r['Product_Name']} ({r['Color']})")
        print(f"     -> Giá: {r['Gia_Khuyen_Mai']:,} đ x {r['Store_Count']} shop = ~{cap_bil:.1f} TỶ VNĐ")

if __name__ == "__main__":
    run_eda("data/hybrid/tgdd_inventory_deep_2026-10-06.json")
