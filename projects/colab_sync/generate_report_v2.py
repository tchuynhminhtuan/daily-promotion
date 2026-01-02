# @title 2. Tải dữ liệu từ GitHub
# @markdown Chạy ô này để tải toàn bộ dữ liệu CSV mới nhất.
import os

# Xóa folder cũ nếu có để đảm bảo lấy dữ liệu mới nhất
if os.path.exists('daily-promotion'):
    !rm -rf daily-promotion

print("⬇️ Đang tải dữ liệu từ GitHub (Chế độ Tối ưu)...")
# 1. Clone không tải file (chỉ lấy khung)
!git clone --depth 1 --filter=blob:none --sparse https://github.com/tchuynhminhtuan/daily-promotion.git

# 2. Vào thư mục và chỉ lấy folder `content` và FILE `code/generate_report.py`
%cd daily-promotion
!git sparse-checkout set content code/generate_report.py
%cd ..

import sys
import re
from google.colab import files

# --- 3. SMART IMPORT (Nhập logic từ Github thay vì copy-paste) ---
# Thêm đường dẫn chứa code vào hệ thống
sys.path.append('/content/daily-promotion')
sys.path.append('/content/daily-promotion/code')

# DEBUG: Kiểm tra xem file có tồn tại không?
import glob
print("📂 Kiểm tra thư mục code:")
try:
    files_in_code = os.listdir('/content/daily-promotion/code')
    if 'generate_report.py' in files_in_code:
        print("   ✅ Đã tìm thấy file 'generate_report.py'")
    else:
        print(f"   ❌ KHÔNG THẤY file generate_report.py! Danh sách file: {files_in_code}")
except Exception as e:
    print(f"   ❌ Lỗi đọc thư mục: {e}")

try:
    # Reload module nếu chạy lại cell để cập nhật code mới nhất
    if 'code.generate_report' in sys.modules:
        del sys.modules['code.generate_report']
    if 'generate_report' in sys.modules:
        del sys.modules['generate_report']
        
    # Cách 1: Import từ package code
    try:
        from code.generate_report import DataLoader, PriceMatrixGenerator, PromoDiffGenerator, BASE_DIR
    except ImportError:
         # Cách 2: Import trực tiếp nếu sys.path đã trỏ vào code
         from generate_report import DataLoader, PriceMatrixGenerator, PromoDiffGenerator, BASE_DIR
         
    print("✅ Đã nhập thành công các thư viện từ Git!")
except ImportError as e:
    print(f"❌ Lỗi nhập thư viện: {e}. Hãy kiểm tra xem bước 'git clone' đã chạy chưa.")

# ==============================================================================
# QUY TRÌNH CHẠY (Interactive Wrapper)
# ==============================================================================

print(f"\n🚀 --- BẮT ĐẦU TẠO BÁO CÁO ĐỐI SOÁT ---")

# Kiểm tra thư mục dữ liệu (nhập từ biến BASE_DIR của script gốc hoặc định nghĩa lại)
BASE_DIR_COLAB = "/content/daily-promotion/content" 

if not os.path.exists(BASE_DIR_COLAB):
    print("❌ Lỗi: Thư mục dữ liệu không tồn tại. Vui lòng kiểm tra lại quá trình Git Clone.")
else:
    # 1. Tìm các ngày có dữ liệu
    date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    try:
        available = sorted([d for d in os.listdir(BASE_DIR_COLAB) if os.path.isdir(os.path.join(BASE_DIR_COLAB, d)) and date_pattern.match(d)], reverse=True)
    except OSError:
        available = []

    if len(available) < 1:
        print("❌ Không tìm thấy thư mục ngày (YYYY-MM-DD) nào trong Drive/Github.")
    else:
        print("\n" + "="*40)
        print("📅 CÁC NGÀY DỮ LIỆU HIỆN CÓ")
        print("="*40)
        for i, d in enumerate(available):
            print(f" [{i}] Ngày: {d}")
        print("="*40)

        try:
            # Nhập lựa chọn ngày
            new_idx = int(input(f"\n👉 Chọn số thứ tự ngày MỚI (Mặc định 0 - {available[0]}): ") or 0)
            old_idx = int(input(f"👉 Chọn số thứ tự ngày CŨ để so sánh (Mặc định 1): ") or 1)

            newer, older = available[new_idx], available[old_idx]
            print(f"\n🔄 Đang so sánh: {older} ➔ {newer}...")

            # 2. Tải dữ liệu (ADAPTED Function Call)
            # Code gốc: load_all_data(dates, base_dir)
            df = DataLoader.load_all_data(dates=[older, newer], base_dir=BASE_DIR_COLAB)
            
            if df.empty:
                print("❌ Không tải được dữ liệu. Kiểm tra các file CSV.")
            else:
                print(f"📊 Đã tải {len(df)} dòng dữ liệu.")

                # 3. Phân tích & Tạo Báo Cáo
                # Ma trận giá (Skip CSV để nhanh)
                price_gen = PriceMatrixGenerator(df, skip_csv=True)
                price_gen.run()

                output_fn = f"Bacao_SoSanh_{older}_vs_{newer}.html"
                
                # Tạo HTML (skip_csv=True, include_all=True để hiện nút lọc Mới/Cũ)
                diff_gen = PromoDiffGenerator(df, price_gen, output_file=output_fn, skip_csv=True, include_all=True)
                diff_gen.run()
                
                # Kiểm tra kết quả
                if os.path.exists(output_fn):
                    print("\n" + "✨"*20)
                    print("🎯 TẠO BÁO CÁO THÀNH CÔNG!")
                    print(f"💾 File đã lưu: {output_fn}")
                    print("✨"*20 + "\n")

                    # 4. Tự động tải xuống (Chỉ hoạt động trên Colab)
                    print("📥 Đang tự động tải báo cáo về máy tính...")
                    files.download(output_fn)
                else:
                    print("✅ Không có thay đổi nào hoặc lỗi tạo file.")
        except Exception as e:
            print(f"⚠️ Có lỗi xảy ra: {e}")
