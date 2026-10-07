"""
Daily Executive Inventory & Affordability Reporting Engine
Tổng hợp dữ liệu thực tế (Ground-Truth Intelligence) từ TGDD API:
1. Giám sát rủi ro cạn hàng quầy thực tế (Critical Stockout: <= 5 shop, Warning: <= 15 shop)
2. Phân bổ độ phủ thị trường trọng điểm (TP.HCM & Hà Nội)
3. Chấm điểm trợ lực tài chính (Direct Discount + Trade-in Subsidy)
"""

import os
import re
import json
import csv
import pandas as pd
from datetime import datetime

from ..config import HYBRID_DATA_DIR, REPORTS_DIR


def generate_markdown_report(df_res: pd.DataFrame, output_payload: dict, latest_md: str, out_md: str, timestamp_str: str):
    """Xuất báo cáo định dạng Markdown trực quan theo từng danh mục."""
    meta = output_payload.get("metadata", {})
    categories = ["iPhone", "MacBook", "iPad", "Apple Watch", "AirPods"]
    cat_display_names = {
        "iPhone": "📱 iPhone",
        "MacBook": "💻 Mac / MacBook",
        "iPad": "📱 iPad",
        "Apple Watch": "⌚ Apple Watch",
        "AirPods": "🎧 AirPods"
    }

    lines = []
    lines.append(f"# 📊 Báo Cáo Tình Báo Tồn Kho & Trợ Lực Tài Chính (TGDD Intelligence)")
    lines.append(f"**Thời gian cập nhật:** `{timestamp_str}` | **Nguồn dữ liệu:** Thế Giới Di Động (3.000 siêu thị)\n")
    lines.append("## 📌 Tổng Quan Chỉ Số Hệ Thống (Ground-Truth Data)")
    lines.append(f"- **Tổng số SKU theo dõi:** `{meta.get('total_skus', 0)}` biến thể")
    lines.append(f"- **Số SKU sẵn hàng tại quầy (>15 shop):** `{meta.get('safe_count', 0)}`")
    lines.append(f"- **Số SKU báo động đỏ cạn kho (<= 5 shop):** `{meta.get('critical_risk_count', 0)}`")
    lines.append(f"- **Số SKU khan hiếm (6 - 15 shop):** `{meta.get('warning_count', 0)}`")
    lines.append(f"- **Số SKU hết hàng / ngừng bán (0 shop):** `{meta.get('out_of_stock_count', 0) + meta.get('discontinued_count', 0)}`\n")
    
    lines.append("---")
    lines.append("## 🚨 1. Cảnh Báo Nguy Cơ Đứt Hàng Theo Từng Danh Mục")
    lines.append("> *Chỉ liệt kê các sản phẩm còn đang kinh doanh nhưng có tồn kho thực tế dưới 15 cửa hàng toàn quốc.* \n")
    
    for cat in categories:
        cat_df = df_res[df_res['Category'] == cat]
        risk_df = cat_df[
            (cat_df['Actual_Store_Count'] > 0) & 
            (cat_df['Actual_Store_Count'] <= 15)
        ].sort_values(by=['Actual_Store_Count', 'Gia_Khuyen_Mai'], ascending=[True, False]).head(5)
        
        label = cat_display_names.get(cat, cat)
        lines.append(f"### {label}")
        if not risk_df.empty:
            lines.append("| Tên sản phẩm & Màu | Tồn kho toàn quốc | TP.HCM | Hà Nội | Giá khuyến mãi | Tình trạng |")
            lines.append("|:---|:---:|:---:|:---:|:---:|:---:|")
            for _, r in risk_df.iterrows():
                c_str = f" ({r['Color']})" if r['Color'] and r['Color'] != 'Default' else ''
                name = f"{r['Product_Name']}{c_str}"
                name_clean = re.sub(r'^(?:Điện thoại|Máy tính bảng|Laptop|Tai nghe Bluetooth|Đồng hồ thông minh)\s+', '', name)
                icon = "🔴 BÁO ĐỘNG ĐỎ" if r['Actual_Store_Count'] <= 5 else "🟡 KHAN HIẾM"
                hcm_cnt = f"{r.get('Store_HCM', 0)} shop"
                hn_cnt = f"{r.get('Store_Hanoi', 0)} shop"
                lines.append(f"| **{name_clean}** | **{r['Actual_Store_Count']} shop** | {hcm_cnt} | {hn_cnt} | {int(r['Gia_Khuyen_Mai']):,}đ | {icon} |")
        else:
            lines.append("*✅ Toàn bộ tồn kho trong danh mục đang ở mức dồi dào (> 15 shop).*")
        lines.append("")

    lines.append("---")
    lines.append("## 🎁 2. Top Sản Phẩm Có Trợ Lực Tài Chính (Affordability) Hời Nhất")
    lines.append("> *🟢 Chỉ xét các sản phẩm **ĐANG KINH DOANH** và **CÒN HÀNG** thực tế tại hệ thống siêu thị.* \n")

    for cat in categories:
        cat_df = df_res[df_res['Category'] == cat]
        in_stock = cat_df[
            (cat_df['Actual_Store_Count'] > 0) & 
            (~cat_df['Status'].isin(['DISCONTINUED', 'OUT_OF_STOCK']))
        ]
        with_pct = in_stock[in_stock['Affordability_Benefit_Pct'] > 0]
        deals = with_pct.sort_values(by=['Affordability_Benefit_Pct', 'Actual_Store_Count'], ascending=[False, False]).head(3) if not with_pct.empty else in_stock.sort_values(by=['Actual_Store_Count', 'Gia_Khuyen_Mai'], ascending=[False, True]).head(2)

        label = cat_display_names.get(cat, cat)
        lines.append(f"### {label}")
        if not deals.empty:
            lines.append("| Tên sản phẩm & Màu | Giá khuyến mãi | Còn hàng | Giảm trực tiếp | Trợ giá thu cũ | Tiết kiệm (%) |")
            lines.append("|:---|:---:|:---:|:---:|:---:|:---:|")
            for _, r in deals.iterrows():
                c_str = f" ({r['Color']})" if r['Color'] and r['Color'] != 'Default' else ''
                name = f"{r['Product_Name']}{c_str}"
                name_clean = re.sub(r'^(?:Điện thoại|Máy tính bảng|Laptop|Tai nghe Bluetooth|Đồng hồ thông minh)\s+', '', name)
                disc_str = f"{int(r['Direct_Discount_VND']):,}đ" if r['Direct_Discount_VND'] >= 50000 else "-"
                trade_str = f"{int(r['Trade_In_Subsidy_VND']):,}đ" if r['Trade_In_Subsidy_VND'] >= 100000 else "-"
                lines.append(f"| **{name_clean}** | {int(r['Gia_Khuyen_Mai']):,}đ | {r['Actual_Store_Count']} shop | {disc_str} | {trade_str} | **{r['Affordability_Benefit_Pct']:.1f}%** |")
        else:
            lines.append("*⚠️ Hiện không có sản phẩm nào trong danh mục còn hàng tại siêu thị.*")
        lines.append("")

    content = "\n".join(lines)
    with open(latest_md, "w", encoding="utf-8") as f:
        f.write(content)
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(content)


def run_inference(data_json_path: str = None) -> str:
    """Xử lý dữ liệu tồn kho thật và xuất bản báo cáo điều hành chuẩn mực."""
    now = datetime.now()
    timestamp_str = now.strftime("%Y-%m-%d_%H%M")

    if not data_json_path:
        data_json_path = os.path.join(HYBRID_DATA_DIR, "tgdd_inventory_deep_latest.json")

    if not os.path.exists(data_json_path):
        raise FileNotFoundError(f"Không tìm thấy tệp dữ liệu tồn kho: {data_json_path}")

    print("=" * 80)
    print(f"📊 BÁO CÁO ĐIỀU HÀNH TỒN KHO & AFFORDABILITY THỰC TẾ - {timestamp_str}")
    print(f"Nguồn dữ liệu: {data_json_path}")
    print("=" * 80)

    with open(data_json_path, encoding='utf-8') as f:
        payload = json.load(f)
    items = payload.get("data", [])
    df_raw = pd.DataFrame(items)

    results = []
    for _, row in df_raw.iterrows():
        actual_st = int(row.get("Store_Count", 0))
        store_hcm = int(row.get("Store_HCM", 0))
        store_hn = int(row.get("Store_Hanoi", 0))
        is_discontinued = bool(row.get("Is_Discontinued", False))

        # Phân loại trạng thái dựa trên số liệu thực tế 100%
        if is_discontinued:
            status = "DISCONTINUED"
        elif actual_st == 0:
            status = "OUT_OF_STOCK"
        elif actual_st <= 5:
            status = "CRITICAL_RISK"
        elif actual_st <= 15:
            status = "WARNING"
        else:
            status = "SAFE"

        # Tính toán mức tiết kiệm tài chính thực tế
        gia_goc = float(row.get("Gia_Niem_Yet", 0))
        giam_truc_tiep = float(row.get("Direct_Discount_VND", 0))
        tro_gia_thucu = float(row.get("Trade_In_Subsidy_VND", 0))
        if gia_goc > 0:
            affordability_benefit_pct = round(((giam_truc_tiep + tro_gia_thucu) / gia_goc) * 100, 1)
        else:
            affordability_benefit_pct = 0.0

        rec = {
            "Product_Name": row.get("Product_Name"),
            "Category": row.get("Category"),
            "Storage": row.get("Storage"),
            "Color": row.get("Color"),
            "SKU": row.get("SKU"),
            "Gia_Niem_Yet": int(gia_goc),
            "Gia_Khuyen_Mai": int(row.get("Gia_Khuyen_Mai", 0)),
            "Actual_Store_Count": actual_st,
            "Store_HCM": store_hcm,
            "Store_Hanoi": store_hn,
            "Status": status,
            "Direct_Discount_VND": int(giam_truc_tiep),
            "Trade_In_Subsidy_VND": int(tro_gia_thucu),
            "Min_Monthly_Payment_12M": row.get("Min_Monthly_Payment_12M", 0),
            "Affordability_Benefit_Pct": affordability_benefit_pct,
            "Link": row.get("Link")
        }
        results.append(rec)

    # Xuất file báo cáo
    os.makedirs(REPORTS_DIR, exist_ok=True)
    out_json = os.path.join(REPORTS_DIR, f"predictions_{timestamp_str}.json")
    latest_json = os.path.join(REPORTS_DIR, "predictions_latest.json")
    latest_csv = os.path.join(REPORTS_DIR, "predictions_latest.csv")
    out_md = os.path.join(REPORTS_DIR, f"daily_report_{timestamp_str}.md")
    latest_md = os.path.join(REPORTS_DIR, "daily_report_latest.md")

    output_payload = {
        "metadata": {
            "report_timestamp": now.isoformat(),
            "source_snapshot": data_json_path,
            "total_skus": len(results),
            "discontinued_count": sum(1 for r in results if r["Status"] == "DISCONTINUED"),
            "out_of_stock_count": sum(1 for r in results if r["Status"] == "OUT_OF_STOCK"),
            "critical_risk_count": sum(1 for r in results if r["Status"] == "CRITICAL_RISK"),
            "warning_count": sum(1 for r in results if r["Status"] == "WARNING"),
            "safe_count": sum(1 for r in results if r["Status"] == "SAFE")
        },
        "inventory_data": results
    }

    with open(out_json, "w", encoding="utf-8") as jf:
        json.dump(output_payload, jf, ensure_ascii=False, indent=2)

    with open(latest_json, "w", encoding="utf-8") as jf:
        json.dump(output_payload, jf, ensure_ascii=False, indent=2)

    df_res = pd.DataFrame(results)
    df_res.to_csv(latest_csv, index=False, sep=";", encoding="utf-8-sig")

    generate_markdown_report(df_res, output_payload, latest_md, out_md, timestamp_str)

    print(f"✅ Hoàn tất xử lý cho {len(results)} biến thể SKU!")
    print(f"📁 Tệp JSON: {latest_json}")
    print(f"📁 Tệp CSV:  {latest_csv}")
    print(f"📄 Tệp Báo Cáo Markdown: {latest_md}")

    # Tóm tắt nhanh ra Terminal
    print("\n" + "=" * 95)
    print("📋 TỔNG KẾT TÌNH HÌNH TỒN KHO THỰC TẾ:")
    print(f"  • Tổng SKU: {len(results)}")
    print(f"  • Đang sẵn hàng (> 15 shop): {output_payload['metadata']['safe_count']}")
    print(f"  • Cảnh báo khan hiếm (6 - 15 shop): {output_payload['metadata']['warning_count']}")
    print(f"  • Báo động đỏ (<= 5 shop): {output_payload['metadata']['critical_risk_count']}")
    print(f"  • Đã cạn sạch / Ngừng bán: {output_payload['metadata']['out_of_stock_count'] + output_payload['metadata']['discontinued_count']}")
    print("=" * 95 + "\n")

    return latest_md


if __name__ == "__main__":
    run_inference()
