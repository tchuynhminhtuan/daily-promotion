#!/usr/bin/env python3
"""
Prototype Feature Engineering & Modeling Experiment on TGDD Inventory Dataset
"""

import json
import re
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.metrics import mean_absolute_error, r2_score, accuracy_score, classification_report

def extract_storage_gb(row):
    storage_str = str(row.get('Storage', ''))
    if 'TB' in storage_str:
        num = re.findall(r'(\d+)\s*TB', storage_str)
        if num:
            return int(num[0]) * 1024
    if 'GB' in storage_str:
        # If Mac format like 16GB/512GB, take the SSD (storage) part
        nums = re.findall(r'(\d+)\s*GB', storage_str)
        if nums:
            return int(nums[-1])
    return 0

def extract_ram_gb(row):
    storage_str = str(row.get('Storage', ''))
    if '/' in storage_str and 'GB' in storage_str:
        nums = re.findall(r'(\d+)\s*GB', storage_str)
        if nums:
            return int(nums[0])
    return 0

def extract_generation(name):
    name = str(name).lower()
    for gen in ['iphone 18', 'iphone 17', 'iphone 16', 'iphone 15', 'iphone 14', 'iphone 13', 'iphone 12', 'iphone 11']:
        if gen in name:
            return gen.title()
    for m in ['m5', 'm4', 'm3', 'm2', 'm1', 'a18 pro']:
        if m in name:
            return f"Mac-{m.upper()}"
    for w in ['ultra 2', 'series 10', 'series 9', 'se 3', 'se 2']:
        if w in name:
            return f"Watch-{w.title()}"
    for a in ['airpods 5', 'airpods 4', 'airpods max', 'airpods pro']:
        if a in name:
            return a.title()
    for ip in ['ipad pro', 'ipad air', 'ipad mini', 'ipad a16']:
        if ip in name:
            return ip.title()
    return 'Other'

def group_color(color_name):
    c = str(color_name).lower()
    if c in ['default', 'none', '']:
        return 'Standard'
    if any(k in c for k in ['đen', 'black', 'xám', 'midnight', 'xanh đậm', 'tối']):
        return 'Dark'
    if any(k in c for k in ['trắng', 'white', 'bạc', 'silver', 'starlight', 'sáng']):
        return 'Light'
    if any(k in c for k in ['cam', 'vàng', 'hồng', 'đỏ', 'tím', 'xanh lá', 'xanh dương', 'vũ trụ']):
        return 'Vibrant'
    return 'Other'

def run_experiment():
    with open('data/hybrid/tgdd_inventory_deep_2026-10-06.json', encoding='utf-8') as f:
        items = json.load(f)['data']

    df = pd.DataFrame(items)
    print("=" * 80)
    print("🤖 FEATURE ENGINEERING & THỬ NGHIỆM MÔ HÌNH HÓA (AI/ML)")
    print(f"Tổng số mẫu (SKUs): {len(df)}")
    print("=" * 80)

    # 1. TRÍCH XUẤT ĐẶC TRƯNG MIỀN (DOMAIN FEATURE EXTRACTION)
    df['Price_Million'] = df['Gia_Khuyen_Mai'] / 1e6
    df['Storage_GB'] = df.apply(extract_storage_gb, axis=1)
    df['RAM_GB'] = df.apply(extract_ram_gb, axis=1)
    df['Generation'] = df['Product_Name'].apply(extract_generation)
    df['Color_Group'] = df['Color'].apply(group_color)
    df['Rating_Count_Num'] = pd.to_numeric(df['Rating_Count'], errors='coerce').fillna(0)
    df['Rating_Score_Num'] = pd.to_numeric(df['Rating_Score'], errors='coerce').fillna(0)
    df['Log_Rating_Count'] = np.log1p(df['Rating_Count_Num'])
    df['Has_Demo'] = (df['Sample_Display_Total'] > 0).astype(int)

    # TARGETS
    df['Target_In_Stock'] = (df['Store_Count'] > 0).astype(int)
    df['Target_Store_Count'] = df['Store_Count'].astype(float)

    # 2. SO SÁNH PHƯƠNG PHÁP MÃ HÓA (ENCODING COMPARISON)
    # Categoricals to encode: Category, Generation, Color_Group
    cat_cols = ['Category', 'Generation', 'Color_Group']
    num_cols = ['Price_Million', 'Storage_GB', 'RAM_GB', 'Log_Rating_Count', 'Rating_Score_Num', 'Has_Demo', 'Sample_Display_Total']

    print("\n[BƯỚC 1] SO SÁNH MA TRẬN ĐẶC TRƯNG KHI DÙNG ONE-HOT ENCODING (OHE):")
    print("-" * 80)
    df_ohe = pd.get_dummies(df[cat_cols], prefix=cat_cols, drop_first=False)
    print(f"• Số chiều biến Categorical gốc: {len(cat_cols)} cột")
    print(f"• Số chiều sau khi One-Hot Encoding: {df_ohe.shape[1]} cột nhị phân (0/1)")
    print(f"  Ví dụ danh sách cột sinh ra:")
    for col in list(df_ohe.columns)[:8]:
        print(f"    - {col}")
    print(f"    ... và {len(df_ohe.columns) - 8} cột khác")

    X = pd.concat([df[num_cols], df_ohe], axis=1)
    y_reg = df['Target_Store_Count']
    y_clf = df['Target_In_Stock']

    print(f"\n• Ma trận huấn luyện cuối cùng X: {X.shape[0]} dòng x {X.shape[1]} đặc trưng (Features)")

    # 3. THỬ NGHIỆM BÀI TOÁN 1: CLASSIFICATION (DỰ ĐOÁN XÁC SUẤT SẢN PHẨM CÒN HÀNG HAY HẾT SẠCH)
    print("\n[BƯỚC 2] BÀI TOÁN 1: DỰ ĐOÁN XÁC SUẤT CÒN HÀNG TOÀN QUỐC (STOCK STATUS CLASSIFICATION)")
    print("-" * 80)
    X_train, X_test, y_train_clf, y_test_clf = train_test_split(X, y_clf, test_size=0.25, random_state=42, stratify=y_clf)
    
    clf = RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42)
    clf.fit(X_train, y_train_clf)
    y_pred_clf = clf.predict(X_test)
    
    acc = accuracy_score(y_test_clf, y_pred_clf)
    print(f"• Độ chính xác (Accuracy): {acc * 100:.2f}%")
    print("• Chi tiết Báo cáo Phân loại:")
    print(classification_report(y_test_clf, y_pred_clf, target_names=['Hết hàng (0)', 'Còn hàng (1)']))

    # 4. THỬ NGHIỆM BÀI TOÁN 2: REGRESSION (DỰ ĐOÁN SỐ LƯỢNG SHOP PHỦ SÓNG - STORE COUNT)
    print("\n[BƯỚC 3] BÀI TOÁN 2: DỰ ĐOÁN ĐỘ PHỦ ĐIỂM BÁN (STORE COUNT REGRESSION)")
    print("-" * 80)
    X_train_r, X_test_r, y_train_r, y_test_r = train_test_split(X, y_reg, test_size=0.25, random_state=42)
    
    reg = RandomForestRegressor(n_estimators=100, max_depth=6, random_state=42)
    reg.fit(X_train_r, y_train_r)
    y_pred_r = reg.predict(X_test_r)
    
    mae = mean_absolute_error(y_test_r, y_pred_r)
    r2 = r2_score(y_test_r, y_pred_r)
    print(f"• Sai số tuyệt đối trung bình (MAE): {mae:.1f} shops")
    print(f"• Hệ số giải thích biến thiên (R² Score): {r2:.3f}")

    # 5. FEATURE IMPORTANCE (ĐẶC TRƯNG NÀO CHI PHỐI QUYẾT ĐỊNH CỦA HỆ THỐNG?)
    print("\n[BƯỚC 4] FEATURE IMPORTANCE (ĐẶC TRƯNG NÀO CÓ SỨC ẢNH HƯỞNG LỚN NHẤT?)")
    print("-" * 80)
    feat_imp = pd.Series(reg.feature_importances_, index=X.columns).sort_values(ascending=False).head(10)
    for feat, imp in feat_imp.items():
        print(f"  {feat:<35} : {imp*100:5.2f}%")

if __name__ == "__main__":
    run_experiment()
