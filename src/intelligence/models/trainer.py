"""
Model Training & Evaluation Engine for TGDD Retail Intelligence
Huấn luyện định kỳ:
1. StockOutClassifier (Dự đoán nguy cơ đứt hàng toàn quốc)
2. StoreCountRegressor (Dự đoán độ phủ quầy kệ)
"""

import os
import json
import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import classification_report, accuracy_score, mean_absolute_error, r2_score

from ..config import MODELS_DIR, HYBRID_DATA_DIR
from ..features.feature_engineering import FeatureEngineer


def train_models(data_json_path: str = None) -> dict:
    if not data_json_path:
        data_json_path = os.path.join(HYBRID_DATA_DIR, "tgdd_inventory_deep_latest.json")

    if not os.path.exists(data_json_path):
        raise FileNotFoundError(f"Không tìm thấy tệp dữ liệu huấn luyện: {data_json_path}")

    print("=" * 80)
    print("🧠 HUẤN LUYỆN MÔ HÌNH AI/ML (RETAIL INTELLIGENCE)")
    print(f"Nguồn dữ liệu: {data_json_path}")
    print("=" * 80)

    with open(data_json_path, encoding='utf-8') as f:
        payload = json.load(f)
    items = payload.get("data", [])
    df_raw = pd.DataFrame(items)

    print(f"• Tổng số mẫu dữ liệu (SKUs): {len(df_raw)}")

    # 1. Feature Engineering
    fe = FeatureEngineer()
    X = fe.fit_transform(df_raw)
    
    # Target 1: Hết hàng (0) vs Còn hàng (1)
    y_in_stock = (df_raw['Store_Count'] > 0).astype(int)
    # Target 2: Số shop có hàng
    y_store_count = df_raw['Store_Count'].astype(float)

    print(f"• Ma trận đặc trưng X: {X.shape[0]} mẫu x {X.shape[1]} thuộc tính")

    # 2. Huấn luyện Model 1: Phân loại nguy cơ hết hàng (Classification)
    print("\n[MÔ HÌNH 1] Huấn luyện Stock-Out Risk Classifier (Random Forest)...")
    X_train_c, X_test_c, y_train_c, y_test_c = train_test_split(
        X, y_in_stock, test_size=0.25, random_state=42, stratify=y_in_stock
    )
    clf = RandomForestClassifier(n_estimators=120, max_depth=6, random_state=42)
    clf.fit(X_train_c, y_train_c)
    y_pred_c = clf.predict(X_test_c)
    acc = accuracy_score(y_test_c, y_pred_c)
    print(f"  ✅ Độ chính xác (Accuracy): {acc * 100:.2f}%")

    # 3. Huấn luyện Model 2: Hồi quy số điểm bán (Regression)
    print("\n[MÔ HÌNH 2] Huấn luyện Store Shelf Distribution Regressor (Random Forest)...")
    X_train_r, X_test_r, y_train_r, y_test_r = train_test_split(
        X, y_store_count, test_size=0.25, random_state=42
    )
    reg = RandomForestRegressor(n_estimators=120, max_depth=6, random_state=42)
    reg.fit(X_train_r, y_train_r)
    y_pred_r = reg.predict(X_test_r)
    mae = mean_absolute_error(y_test_r, y_pred_r)
    r2 = r2_score(y_test_r, y_pred_r)
    print(f"  ✅ Sai số tuyệt đối (MAE): {mae:.1f} shops | R² Score: {r2:.3f}")

    # 4. Lưu Model Artifacts
    os.makedirs(MODELS_DIR, exist_ok=True)
    fe_path = os.path.join(MODELS_DIR, "feature_engineer.pkl")
    clf_path = os.path.join(MODELS_DIR, "stockout_classifier.pkl")
    reg_path = os.path.join(MODELS_DIR, "store_regressor.pkl")

    fe.save(fe_path)
    joblib.dump(clf, clf_path)
    joblib.dump(reg, reg_path)

    print("\n[LƯU MÔ HÌNH] Đã xuất bản Model Artifacts thành công:")
    print(f"  💾 Feature Engineer: {fe_path}")
    print(f"  💾 Stock-Out Model:  {clf_path}")
    print(f"  💾 Shelf Regressor:  {reg_path}")
    print("=" * 80)

    return {
        "clf_accuracy": acc,
        "reg_mae": mae,
        "reg_r2": r2,
        "n_samples": len(df_raw),
        "n_features": X.shape[1]
    }


if __name__ == "__main__":
    train_models()
