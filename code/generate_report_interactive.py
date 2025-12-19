import os
import re
import sys
import pandas as pd
from generate_report import DataLoader, PriceMatrixGenerator, PromoDiffGenerator, COLUMN_MAPPING, BASE_DIR

# --- Configuration Override ---
# You can set an environment variable BASE_DIR to point to Google Drive
# Set your preferred cloud path as the default fallback
GD_PATH = "/Users/brucehuynh/Library/CloudStorage/GoogleDrive-tchuynhminhtuan@gmail.com/My Drive/Daily_Promotion_Data"
CLOUD_BASE_DIR = os.getenv("DAILY_PROMOTION_BASE_DIR", GD_PATH if os.path.exists(GD_PATH) else BASE_DIR)

class PriceMatrixGeneratorNoCSV(PriceMatrixGenerator):
    """Overrides CSV generation to skip it."""
    def _generate_csv(self, df):
        # We still need to do everything else in run(), 
        # but we skip the actual .to_csv part.
        print("💡 Đang xử lý Ma trận Giá (Bỏ qua lưu file CSV)...")
        pass

class PromoDiffGeneratorNoCSV(PromoDiffGenerator):
    """Overrides CSV generation to skip it."""
    def run(self):
        print("🔍 Đang phân tích thay đổi khuyến mãi...")
        if self.df.empty: return
        df_collapsed = self._collapse_for_promo(self.df)
        df_diff = self._identify_changes(df_collapsed)
        
        if df_diff is not None and not df_diff.empty:
            # Skip the df_diff.to_csv part
            print("🌐 Đang tạo file báo cáo HTML (Bỏ qua lưu file CSV)...")
            self._save_html(df_diff)
        else:
            print("✅ Không tìm thấy thay đổi nào về khuyến mãi.")

def get_available_dates(base_path):
    if not os.path.exists(base_path):
        print(f"Error: Base directory not found: {base_path}")
        return []
    
    # regex for YYYY-MM-DD
    date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    dates = [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d)) and date_pattern.match(d)]
    return sorted(dates, reverse=True)

def select_dates(available_dates):
    if not available_dates:
        print("❌ Không tìm thấy thư mục dữ liệu nào trong BASE_DIR.")
        return None, None

    print("\n" + "="*40)
    print("📅 CÁC NGÀY CÓ DỮ LIỆU HIỆN CÓ")
    print("="*40)
    for i, d in enumerate(available_dates):
        print(f" [{i}] Ngày: {d}")
    print("="*40)
    
    try:
        new_prompt = f"\n👉 Chọn số thứ tự ngày MỚI NHẤT [Mặc định 0 ({available_dates[0]})]: "
        new_idx = int(input(new_prompt) or 0)
        
        default_old = min(1, len(available_dates)-1)
        old_prompt = f"👉 Chọn số thứ tự ngày CŨ HƠN để so sánh [Mặc định {default_old} ({available_dates[default_old]})]: "
        old_idx = int(input(old_prompt) or default_old)
        
        if new_idx < 0 or new_idx >= len(available_dates) or old_idx < 0 or old_idx >= len(available_dates):
            print("⚠️ Lựa chọn không hợp lệ. Vui lòng thử lại.")
            return None, None
            
        return available_dates[new_idx], available_dates[old_idx]
    except ValueError:
        print("⚠️ Vui lòng chỉ nhập số thứ tự từ danh sách trên.")
        return None, None

def main():
    print(f"\n🚀 --- BẮT ĐẦU TẠO BÁO CÁO ĐỐI SOÁT (CHỈ HTML) ---")
    print(f"📁 Thư mục nguồn: {CLOUD_BASE_DIR}")
    
    available = get_available_dates(CLOUD_BASE_DIR)
    newer_date, older_date = select_dates(available)
    
    if not newer_date or not older_date:
        print("❌ Quá trình chọn ngày bị hủy hoặc thất bại.")
        return

    print(f"\n🔄 Đang so sánh: {older_date} (Cũ) ➔ {newer_date} (Mới)...")
    
    # We must patch the global DATES in generate_report temporarily because DataLoader uses it
    import generate_report
    generate_report.DATES = [older_date, newer_date]
    generate_report.BASE_DIR = CLOUD_BASE_DIR # Ensure DataLoader uses the correct base
    
    # 1. Load Data
    print("📥 Đang tải dữ liệu từ CSV...")
    df = DataLoader.load_all_data()
    print(f"📊 Tổng số sản phẩm đã tải: {len(df)}")
    if df.empty:
        print("❌ Không tìm thấy dữ liệu cho các ngày đã chọn.")
        return
    
    # 2. Price Lookup (using our No-CSV version)
    price_gen = PriceMatrixGeneratorNoCSV(df)
    price_gen.run()
    
    # 3. Promo Diff & HTML (using our No-CSV version)
    promo_gen = PromoDiffGeneratorNoCSV(df, price_gen)
    promo_gen.run()
    
    print("\n" + "✨"*20)
    print("🎯 TẠO BÁO CÁO THÀNH CÔNG!")
    print(f"📌 Xem báo cáo tại: {os.path.abspath(generate_report.PROMO_DIFF_HTML)}")
    print("✨"*20 + "\n")

if __name__ == "__main__":
    main()
