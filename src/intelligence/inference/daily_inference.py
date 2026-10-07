"""
Daily AI Inference & Scoring Pipeline
Thực thi tự động sau mỗi lượt quét snapshot để:
1. Dự báo nguy cơ đứt hàng (Stock-Out Probability & Risk Level)
2. Dự báo độ phủ quầy kệ (Predicted Shelf Distribution)
3. Chấm điểm trợ lực tài chính (Affordability Attractiveness Score)
"""

import os
import re
import json
import joblib
import pandas as pd
from datetime import datetime

from ..config import MODELS_DIR, HYBRID_DATA_DIR, PREDICTIONS_DIR
from ..features.feature_engineering import FeatureEngineer


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
    lines.append(f"# 🧠 Báo Cáo Dự Báo Tồn Kho & Trợ Lực Tài Chính (TGDD Intelligence)")
    lines.append(f"**Thời gian cập nhật:** `{timestamp_str}` | **Nguồn dữ liệu:** Thế Giới Di Động (3.000 siêu thị)\n")
    lines.append("## 📌 Tổng Quan Chỉ Số Hệ Thống")
    lines.append(f"- **Tổng số SKU theo dõi:** `{meta.get('total_skus', 0)}` biến thể")
    lines.append(f"- **Số SKU còn hàng tại quầy:** `{meta.get('safe_count', 0) + meta.get('critical_risk_count', 0)}`")
    lines.append(f"- **Số SKU cảnh báo đứt hàng (Critical Risk):** `{meta.get('critical_risk_count', 0)}`")
    lines.append(f"- **Số SKU hết hàng / ngừng kinh doanh:** `{meta.get('out_of_stock_count', 0) + meta.get('discontinued_count', 0)}`\n")
    
    lines.append("---")
    lines.append("## 🚨 1. Cảnh Báo Nguy Cơ Đứt Hàng Theo Từng Danh Mục")
    lines.append("> *Chỉ liệt kê các sản phẩm còn đang kinh doanh nhưng có tồn kho dưới 15 cửa hàng toàn quốc.* \n")
    
    for cat in categories:
        cat_df = df_res[df_res['Category'] == cat]
        risk_df = cat_df[
            (cat_df['Actual_Store_Count'] > 0) & 
            (cat_df['Risk_Level'].isin(['CRITICAL_RISK', 'WARNING']) | (cat_df['Actual_Store_Count'] <= 15))
        ].sort_values(by=['Actual_Store_Count', 'Stockout_Probability'], ascending=[True, False]).head(3)
        
        label = cat_display_names.get(cat, cat)
        lines.append(f"### {label}")
        if not risk_df.empty:
            lines.append("| Tên sản phẩm & Màu | Tồn kho thực tế | Dự báo AI | Xác suất cạn | Giá khuyến mãi | Mức rủi ro |")
            lines.append("|:---|:---:|:---:|:---:|:---:|:---:|")
            for _, r in risk_df.iterrows():
                c_str = f" ({r['Color']})" if r['Color'] and r['Color'] != 'Default' else ''
                name = f"{r['Product_Name']}{c_str}"
                name_clean = re.sub(r'^(?:Điện thoại|Máy tính bảng|Laptop|Tai nghe Bluetooth|Đồng hồ thông minh)\s+', '', name)
                icon = "🔴 CRITICAL" if r['Risk_Level'] == 'CRITICAL_RISK' or r['Actual_Store_Count'] <= 5 else "🟡 WARNING"
                lines.append(f"| **{name_clean}** | {r['Actual_Store_Count']} shop | {r['Predicted_Store_Count']} shop | {r['Stockout_Probability']*100:.1f}% | {int(r['Gia_Khuyen_Mai']):,}đ | {icon} |")
        else:
            lines.append("*✅ Toàn bộ tồn kho trong danh mục đang ở mức an toàn.*")
        lines.append("")

    lines.append("---")
    lines.append("## 🎁 2. Top Sản Phẩm Có Trợ Lực Tài Chính (Affordability) Hời Nhất")
    lines.append("> *🟢 Chỉ xét các sản phẩm **ĐANG KINH DOANH** và **CÒN HÀNG** thực tế tại hệ thống siêu thị.* \n")

    for cat in categories:
        cat_df = df_res[df_res['Category'] == cat]
        in_stock = cat_df[
            (cat_df['Actual_Store_Count'] > 0) & 
            (~cat_df['Risk_Level'].isin(['DISCONTINUED', 'OUT_OF_STOCK']))
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

    now = datetime.now()
    timestamp_str = now.strftime("%Y-%m-%d_%H%M")

    if not data_json_path:
        data_json_path = os.path.join(HYBRID_DATA_DIR, "tgdd_inventory_deep_latest.json")

    fe_path = os.path.join(MODELS_DIR, "feature_engineer.pkl")
    clf_path = os.path.join(MODELS_DIR, "stockout_classifier.pkl")
    reg_path = os.path.join(MODELS_DIR, "store_regressor.pkl")

    # Kiểm tra xem models đã train chưa, nếu chưa thì tự động train lần đầu
    if not (os.path.exists(fe_path) and os.path.exists(clf_path) and os.path.exists(reg_path)):
        print("⚠️ Chưa tìm thấy Model đã lưu. Đang kích hoạt huấn luyện tự động lần đầu...")
        from ..models.trainer import train_models
        train_models(data_json_path)

    fe = FeatureEngineer.load(fe_path)
    clf = joblib.load(clf_path)
    reg = joblib.load(reg_path)

    print("=" * 80)
    print(f"🔮 CHẠY MÔ HÌNH DỰ BÁO AI/ML HÀNG NGÀY - {timestamp_str}")
    print(f"Dữ liệu đầu vào: {data_json_path}")
    print("=" * 80)

    with open(data_json_path, encoding='utf-8') as f:
        payload = json.load(f)
    items = payload.get("data", [])
    df_raw = pd.DataFrame(items)

    # 1. Feature Transformation
    X = fe.transform(df_raw)

    # 2. Inference: Xác suất Còn hàng vs Hết hàng
    # Classes: [0: Hết hàng, 1: Còn hàng]
    probas = clf.predict_proba(X)
    classes = list(clf.classes_)
    idx_out_of_stock = classes.index(0) if 0 in classes else None

    if idx_out_of_stock is not None:
        stockout_probas = probas[:, idx_out_of_stock]
    else:
        stockout_probas = [0.0] * len(df_raw)

    predicted_stores = reg.predict(X)

    # 3. Tổng hợp kết quả dự báo
    results = []
    for idx, row in df_raw.iterrows():
        p_stockout = float(stockout_probas[idx])
        pred_st = max(0, int(round(float(predicted_stores[idx]))))
        actual_st = int(row.get("Store_Count", 0))

        # Phân loại mức độ rủi ro (Risk Level)
        is_discontinued = bool(row.get("Is_Discontinued", False))
        if is_discontinued:
            risk_level = "DISCONTINUED"
        elif actual_st == 0:
            risk_level = "OUT_OF_STOCK"
        elif p_stockout >= 0.70 or actual_st <= 5:
            risk_level = "CRITICAL_RISK"
        elif p_stockout >= 0.35 or actual_st <= 20:
            risk_level = "WARNING"
        else:
            risk_level = "SAFE"

        # Tính chỉ số hấp dẫn tài chính (% giảm trực tiếp + trợ giá thu cũ so với giá niêm yết)
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
            "Gia_Khuyen_Mai": row.get("Gia_Khuyen_Mai"),
            "Actual_Store_Count": actual_st,
            "Predicted_Store_Count": pred_st,
            "Stockout_Probability": round(p_stockout, 3),
            "Risk_Level": risk_level,
            "Is_Discontinued": is_discontinued,
            "Direct_Discount_VND": int(giam_truc_tiep),
            "Trade_In_Subsidy_VND": int(tro_gia_thucu),
            "Min_Monthly_Payment_12M": row.get("Min_Monthly_Payment_12M", 0),
            "Affordability_Benefit_Pct": affordability_benefit_pct,
            "Link": row.get("Link")
        }
        results.append(rec)

    # 4. Xuất file dự báo
    os.makedirs(PREDICTIONS_DIR, exist_ok=True)
    out_json = os.path.join(PREDICTIONS_DIR, f"predictions_{timestamp_str}.json")
    latest_json = os.path.join(PREDICTIONS_DIR, "predictions_latest.json")
    latest_csv = os.path.join(PREDICTIONS_DIR, "predictions_latest.csv")
    out_md = os.path.join(PREDICTIONS_DIR, f"daily_report_{timestamp_str}.md")
    latest_md = os.path.join(PREDICTIONS_DIR, "daily_report_latest.md")

    output_payload = {
        "metadata": {
            "prediction_timestamp": now.isoformat(),
            "source_snapshot": data_json_path,
            "total_skus": len(results),
            "discontinued_count": sum(1 for r in results if r["Risk_Level"] == "DISCONTINUED"),
            "out_of_stock_count": sum(1 for r in results if r["Risk_Level"] == "OUT_OF_STOCK"),
            "critical_risk_count": sum(1 for r in results if r["Risk_Level"] == "CRITICAL_RISK"),
            "safe_count": sum(1 for r in results if r["Risk_Level"] == "SAFE")
        },
        "predictions": results
    }

    with open(out_json, "w", encoding="utf-8") as jf:
        json.dump(output_payload, jf, ensure_ascii=False, indent=2)

    with open(latest_json, "w", encoding="utf-8") as jf:
        json.dump(output_payload, jf, ensure_ascii=False, indent=2)

    df_res = pd.DataFrame(results)
    df_res.to_csv(latest_csv, index=False, sep=";", encoding="utf-8-sig")

    # Xuất báo cáo Markdown trực quan
    generate_markdown_report(df_res, output_payload, latest_md, out_md, timestamp_str)

    print(f"✅ Dự báo hoàn tất cho {len(results)} biến thể SKU!")
    print(f"📁 Tệp kết quả: {out_json}")
    print(f"📄 Báo cáo Markdown: {latest_md}")
    print(f"🔗 Tệp mới nhất: {latest_json} & {latest_csv}")


    # 5. In tóm tắt cảnh báo kinh doanh theo từng danh mục
    def format_sku_name(name: str, color: str, max_len: int = 34) -> str:
        color_str = f" ({color})" if color and color != "Default" else ""
        full = f"{name}{color_str}"
        full = re.sub(r'^(?:Điện thoại|Máy tính bảng|Laptop|Tai nghe Bluetooth|Đồng hồ thông minh)\s+', '', full)
        if len(full) > max_len:
            return full[:max_len-3] + "..."
        return full

    categories = ["iPhone", "MacBook", "iPad", "Apple Watch", "AirPods"]
    cat_display_names = {
        "iPhone": "📱 iPhone",
        "MacBook": "💻 Mac / MacBook",
        "iPad": "📱 iPad",
        "Apple Watch": "⌚ Apple Watch",
        "AirPods": "🎧 AirPods"
    }

    print("\n" + "=" * 98)
    print("🚨 [1] CẢNH BÁO NGUY CƠ ĐỨT HÀNG THEO TỪNG DANH MỤC (STOCK-OUT RISK BY CATEGORY)")
    print("    (Chỉ xét các sản phẩm còn đang lưu hành và còn dưới 20 điểm bán toàn quốc)")
    print("=" * 98)

    for cat in categories:
        cat_df = df_res[df_res['Category'] == cat]
        risk_df = cat_df[
            (cat_df['Actual_Store_Count'] > 0) & 
            (cat_df['Risk_Level'].isin(['CRITICAL_RISK', 'WARNING']) | (cat_df['Actual_Store_Count'] <= 15))
        ].sort_values(by=['Actual_Store_Count', 'Stockout_Probability'], ascending=[True, False]).head(3)

        label = cat_display_names.get(cat, cat)
        print(f"\n{label} ({len(cat_df)} SKUs):")
        if not risk_df.empty:
            for _, r in risk_df.iterrows():
                name_str = format_sku_name(r['Product_Name'], r['Color'], 34)
                stores_str = f"{r['Actual_Store_Count']} shop"
                pred_str = f"{r['Predicted_Store_Count']} shop"
                prob_str = f"{r['Stockout_Probability']*100:.1f}%"
                price_str = f"{int(r['Gia_Khuyen_Mai']):,}đ"
                risk_icon = "🔴 CRITICAL" if r['Risk_Level'] == 'CRITICAL_RISK' or r['Actual_Store_Count'] <= 5 else "🟡 WARNING"
                print(f"  • {name_str:<35} | Tồn: {stores_str:<8} | AI đoán: {pred_str:<7} | Xác suất cạn: {prob_str:<6} | Giá: {price_str:<12} | {risk_icon}")
        else:
            print("  ✅ Toàn bộ tồn kho trong danh mục đang ở mức an toàn (Safe stock level).")

    print("\n" + "=" * 98)
    print("🎁 [2] TOP SẢN PHẨM CÓ TRỢ LỰC TÀI CHÍNH (AFFORDABILITY) HỜI NHẤT THEO TỪNG DANH MỤC")
    print("    (🟢 Chỉ lọc các sản phẩm ĐANG KINH DOANH và CÒN HÀNG tại hệ thống siêu thị)")
    print("=" * 98)

    for cat in categories:
        cat_df = df_res[df_res['Category'] == cat]
        in_stock_deals = cat_df[
            (cat_df['Actual_Store_Count'] > 0) & 
            (~cat_df['Risk_Level'].isin(['DISCONTINUED', 'OUT_OF_STOCK']))
        ]
        
        with_pct = in_stock_deals[in_stock_deals['Affordability_Benefit_Pct'] > 0]
        if not with_pct.empty:
            deals_sorted = with_pct.sort_values(
                by=['Affordability_Benefit_Pct', 'Actual_Store_Count'], 
                ascending=[False, False]
            ).head(3)
        else:
            deals_sorted = in_stock_deals.sort_values(
                by=['Actual_Store_Count', 'Gia_Khuyen_Mai'], 
                ascending=[False, True]
            ).head(2)

        label = cat_display_names.get(cat, cat)
        print(f"\n{label}:")
        if not deals_sorted.empty:
            for _, r in deals_sorted.iterrows():
                name_str = format_sku_name(r['Product_Name'], r['Color'], 34)
                price_str = f"{int(r['Gia_Khuyen_Mai']):,}đ"
                stores_str = f"{r['Actual_Store_Count']} shop"
                disc_val = int(r['Direct_Discount_VND'])
                trade_val = int(r['Trade_In_Subsidy_VND'])
                pct_val = r['Affordability_Benefit_Pct']
                
                if pct_val > 0:
                    disc_str = f"Giảm: {disc_val:,}đ" if disc_val >= 50000 else ""
                    trade_str = f"Thu cũ: +{trade_val:,}đ" if trade_val >= 100000 else ""
                    promo_details = " | ".join(filter(None, [disc_str, trade_str])) or "Ưu đãi tài chính đặc biệt"
                    print(f"  • {name_str:<35} | Giá: {price_str:<12} | Còn: {stores_str:<8} | Tiết kiệm: {pct_val:>4.1f}% ({promo_details})")

                else:
                    monthly = int(r.get('Min_Monthly_Payment_12M', 0))
                    monthly_str = f"Trả chậm 0%: ~{monthly:,}đ/tháng" if monthly > 0 else "Giá niêm yết chuẩn"
                    print(f"  • {name_str:<35} | Giá: {price_str:<12} | Còn: {stores_str:<8} | {monthly_str}")
        else:
            print("  ⚠️ Không có sản phẩm nào trong danh mục còn hàng tại siêu thị.")

    print("\n" + "=" * 98 + "\n")

    return out_json



if __name__ == "__main__":
    run_inference()
