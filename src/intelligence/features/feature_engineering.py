"""
Feature Engineering Engine for TGDD Retail Intelligence
Xử lý đặc trưng hỗn hợp: OHE (Category, Color_Group, Gen) + Numeric Scaling (Storage, RAM, Giá, Affordability).
"""

import os
import re
import joblib
import numpy as np
import pandas as pd
from typing import Tuple, List, Optional
from sklearn.preprocessing import OneHotEncoder

from ..config import CATEGORICAL_FEATURES, NUMERIC_FEATURES


class FeatureEngineer:
    """Đóng gói toàn bộ quy trình trích xuất và biến đổi đặc trưng (Fit/Transform)."""

    def __init__(self):
        self.encoder: Optional[OneHotEncoder] = None
        self.feature_columns: List[str] = []

    @staticmethod
    def extract_storage_gb(row: pd.Series) -> int:
        storage_str = str(row.get('Storage', ''))
        if 'TB' in storage_str:
            num = re.findall(r'(\d+)\s*TB', storage_str)
            if num:
                return int(num[0]) * 1024
        if 'GB' in storage_str:
            nums = re.findall(r'(\d+)\s*GB', storage_str)
            if nums:
                return int(nums[-1])
        return 0

    @staticmethod
    def extract_ram_gb(row: pd.Series) -> int:
        storage_str = str(row.get('Storage', ''))
        if '/' in storage_str and 'GB' in storage_str:
            nums = re.findall(r'(\d+)\s*GB', storage_str)
            if nums:
                return int(nums[0])
        return 0

    @staticmethod
    def extract_generation(name: str) -> str:
        name_lower = str(name).lower()
        for gen in ['iphone 18', 'iphone 17', 'iphone 16', 'iphone 15', 'iphone 14', 'iphone 13', 'iphone 12', 'iphone 11']:
            if gen in name_lower:
                return gen.title()
        for m in ['m5', 'm4', 'm3', 'm2', 'm1', 'a18 pro']:
            if m in name_lower:
                return f"Mac-{m.upper()}"
        for w in ['ultra 2', 'series 11', 'series 10', 'series 9', 'se 3', 'se 2']:
            if w in name_lower:
                return f"Watch-{w.title()}"
        for a in ['airpods 5', 'airpods 4', 'airpods max', 'airpods pro']:
            if a in name_lower:
                return a.title()
        for ip in ['ipad pro', 'ipad air', 'ipad mini', 'ipad a16']:
            if ip in name_lower:
                return ip.title()
        return 'Other'

    @staticmethod
    def group_color(color_name: str) -> str:
        c = str(color_name).lower()
        if c in ['default', 'none', '', 'nan']:
            return 'Standard'
        if any(k in c for k in ['đen', 'black', 'xám', 'midnight', 'xanh đậm', 'tối']):
            return 'Dark'
        if any(k in c for k in ['trắng', 'white', 'bạc', 'silver', 'starlight', 'sáng']):
            return 'Light'
        if any(k in c for k in ['cam', 'vàng', 'hồng', 'đỏ', 'tím', 'xanh lá', 'xanh dương', 'vũ trụ']):
            return 'Vibrant'
        return 'Other'

    def extract_domain_features(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        """Trích xuất các đặc trưng miền cơ sở từ DataFrame thô."""
        df = df_raw.copy()

        # 1. Dung lượng & Cấu hình
        df['Storage_GB'] = df.apply(self.extract_storage_gb, axis=1)
        df['RAM_GB'] = df.apply(self.extract_ram_gb, axis=1)
        df['Generation'] = df['Product_Name'].apply(self.extract_generation)
        df['Color_Group'] = df['Color'].apply(self.group_color)

        # 2. Giá & Affordability
        df['Price_Million'] = pd.to_numeric(df['Gia_Khuyen_Mai'], errors='coerce').fillna(0) / 1e6
        df['Direct_Discount_VND'] = pd.to_numeric(df.get('Direct_Discount_VND', 0), errors='coerce').fillna(0) / 1e6
        df['Trade_In_Subsidy_VND'] = pd.to_numeric(df.get('Trade_In_Subsidy_VND', 0), errors='coerce').fillna(0) / 1e6
        df['Min_Monthly_Payment_12M'] = pd.to_numeric(df.get('Min_Monthly_Payment_12M', 0), errors='coerce').fillna(0) / 1e6
        df['Installment_0_Percent'] = df.get('Installment_0_Percent', False).astype(int)

        # 3. Social Proof (Ratings)
        df['Rating_Count_Num'] = pd.to_numeric(df['Rating_Count'], errors='coerce').fillna(0)
        df['Rating_Score_Num'] = pd.to_numeric(df['Rating_Score'], errors='coerce').fillna(0)
        df['Log_Rating_Count'] = np.log1p(df['Rating_Count_Num'])

        # 4. Trưng bày (Demo Flag)
        sample_total = pd.to_numeric(df.get('Sample_Display_Total', 0), errors='coerce').fillna(0)
        df['Sample_Display_Total'] = sample_total
        df['Has_Demo'] = (sample_total > 0).astype(int)

        return df

    def fit(self, df_raw: pd.DataFrame) -> "FeatureEngineer":
        """Huấn luyện bộ mã hóa One-Hot Encoding."""
        df = self.extract_domain_features(df_raw)
        
        self.encoder = OneHotEncoder(sparse_output=False, handle_unknown='ignore')
        self.encoder.fit(df[CATEGORICAL_FEATURES])
        
        ohe_cols = list(self.encoder.get_feature_names_out(CATEGORICAL_FEATURES))
        self.feature_columns = NUMERIC_FEATURES + ohe_cols
        return self

    def transform(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        """Biến đổi dữ liệu mới thành ma trận đặc trưng chuẩn hóa cho mô hình."""
        if not self.encoder:
            raise ValueError("FeatureEngineer chưa được fit. Hãy gọi fit() trước khi transform()!")

        df = self.extract_domain_features(df_raw)

        # One-Hot Encoding
        ohe_matrix = self.encoder.transform(df[CATEGORICAL_FEATURES])
        ohe_cols = list(self.encoder.get_feature_names_out(CATEGORICAL_FEATURES))
        df_ohe = pd.DataFrame(ohe_matrix, columns=ohe_cols, index=df.index)

        # Ghép Numeric + OHE
        X = pd.concat([df[NUMERIC_FEATURES], df_ohe], axis=1)
        
        # Đảm bảo đúng thứ tự cột
        X = X[self.feature_columns]
        return X

    def fit_transform(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        return self.fit(df_raw).transform(df_raw)

    def save(self, filepath: str):
        """Lưu trạng thái FeatureEngineer ra đĩa."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        joblib.dump({
            "encoder": self.encoder,
            "feature_columns": self.feature_columns
        }, filepath)

    @classmethod
    def load(cls, filepath: str) -> "FeatureEngineer":
        """Tải FeatureEngineer đã lưu từ đĩa."""
        payload = joblib.load(filepath)
        fe = cls()
        fe.encoder = payload["encoder"]
        fe.feature_columns = payload["feature_columns"]
        return fe
