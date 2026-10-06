"""
Daily AI Inference & Scoring Pipeline
Thực thi tự động sau mỗi lượt quét snapshot để:
1. Dự báo nguy cơ đứt hàng (Stock-Out Probability & Risk Level)
2. Dự báo độ phủ quầy kệ (Predicted Shelf Distribution)
3. Chấm điểm trợ lực tài chính (Affordability Attractiveness Score)
"""

import os
import json
import joblib
import pandas as pd
from datetime import datetime

from ..config import MODELS_DIR, HYBRID_DATA_DIR, PREDICTIONS_DIR
from ..features.feature_engineering import FeatureEngineer


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
        if actual_st == 0:
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

    output_payload = {
        "metadata": {
            "prediction_timestamp": now.isoformat(),
            "source_snapshot": data_json_path,
            "total_skus": len(results),
            "critical_risk_count": sum(1 for r in results if r["Risk_Level"] in ["CRITICAL_RISK", "OUT_OF_STOCK"]),
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

    print(f"✅ Dự báo hoàn tất cho {len(results)} biến thể SKU!")
    print(f"📁 Tệp kết quả: {out_json}")
    print(f"🔗 Tệp mới nhất: {latest_json} & {latest_csv}")

    # 5. In tóm tắt cảnh báo kinh doanh
    print("\n🚨 TOP SẢN PHẨM CẢNH BÁO NGUY CƠ ĐỨT HÀNG CAO (CRITICAL RISK):")
    print("-" * 80)
    crit_df = df_res[df_res['Risk_Level'] == 'CRITICAL_RISK'][['Product_Name', 'Color', 'Actual_Store_Count', 'Stockout_Probability', 'Gia_Khuyen_Mai']].head(6)
    if not crit_df.empty:
        print(crit_df.to_string(index=False))
    else:
        print("  Không có sản phẩm nào chạm ngưỡng rủi ro nghiêm trọng.")

    print("\n🎁 TOP SẢN PHẨM CÓ TRỢ LỰC TÀI CHÍNH (AFFORDABILITY) HẤP DẪN NHẤT:")
    print("-" * 80)
    deal_df = df_res.sort_values(by='Affordability_Benefit_Pct', ascending=False)[['Product_Name', 'Color', 'Gia_Khuyen_Mai', 'Direct_Discount_VND', 'Trade_In_Subsidy_VND', 'Affordability_Benefit_Pct']].head(5)
    print(deal_df.to_string(index=False))
    print("=" * 80)

    return out_json


if __name__ == "__main__":
    run_inference()
