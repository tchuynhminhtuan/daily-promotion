# @title 2. Tải dữ liệu từ GitHub (Chế độ Siêu Tối ưu)
# @markdown Chạy ô này để tải dữ liệu (Chỉ tải 'content' và file code chính).
import os
import sys
import shutil

# 1. Clean previous runs
if os.path.exists('daily-promotion'):
    !rm -rf daily-promotion
if os.path.exists('generate_report.py'):
    os.remove('generate_report.py')

print("⬇️ Đang tải dữ liệu từ GitHub (Chế độ Siêu Tối ưu)...")
# 2. Clone sparse (Lite mode)
!git clone --depth 1 --filter=blob:none --sparse https://github.com/tchuynhminhtuan/daily-promotion.git

# 3. Checkout specific folders/files
%cd daily-promotion
!git sparse-checkout set content code/generate_report.py
%cd ..

# 4. START IMPORTS
try:
    # MOVE STRATEGY: Copy file to root for easy import
    source_code = '/content/daily-promotion/code/generate_report.py'
    dest_code = '/content/generate_report.py'
    
    if os.path.exists(source_code):
        shutil.copy(source_code, dest_code)
        print("✅ Đã copy generate_report.py ra thư mục gốc.")
    else:
        print(f"❌ KHÔNG TÌM THẤY FILE GỐC: {source_code}")
        # List folder code to debug
        print("Debug listing code folder:")
        if os.path.exists('/content/daily-promotion/code'):
             print(os.listdir('/content/daily-promotion/code'))
        else:
             print("Folder code không tồn tại!")

    # Reload if exists
    if 'generate_report' in sys.modules:
        del sys.modules['generate_report']

    # Import directly from current folder
    from generate_report import DataLoader, PriceMatrixGenerator, PromoDiffGenerator
    print("✅ Đã nhập thư viện thành công!")
    
except ImportError as e:
    print(f"❌ Lỗi nhập thư viện (CRITICAL): {e}")
    sys.exit("Dừng chương trình do lỗi nhập thư viện.")
except Exception as e:
    print(f"❌ Lỗi không xác định: {e}")
    sys.exit("Dừng chương trình.")

# ==============================================================================
# QUY TRÌNH CHẠY (Interactive Wrapper)
# ==============================================================================
import re
from google.colab import files

print(f"\n🚀 --- BẮT ĐẦU TẠO BÁO CÁO ĐỐI SOÁT ---")

# Data location
BASE_DIR_COLAB = "/content/daily-promotion/content" 

if not os.path.exists(BASE_DIR_COLAB):
    print("❌ Lỗi: Thư mục dữ liệu không tồn tại. Vui lòng kiểm tra lại quá trình Git Clone.")
else:
    # Find Dates
    date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    try:
        available = sorted([d for d in os.listdir(BASE_DIR_COLAB) if os.path.isdir(os.path.join(BASE_DIR_COLAB, d)) and date_pattern.match(d)], reverse=True)
    except OSError:
        available = []

    if len(available) < 1:
        print("❌ Không tìm thấy thư mục ngày (YYYY-MM-DD) nào.")
    else:
        print("\n" + "="*40)
        print("📅 CÁC NGÀY DỮ LIỆU HIỆN CÓ")
        print("="*40)
        for i, d in enumerate(available):
            print(f" [{i}] Ngày: {d}")
        print("="*40)

        try:
            # Inputs
            new_idx = int(input(f"\n👉 Chọn số thứ tự ngày MỚI (Mặc định 0 - {available[0]}): ") or 0)
            old_idx = int(input(f"👉 Chọn số thứ tự ngày CŨ để so sánh (Mặc định 1): ") or 1)

            newer, older = available[new_idx], available[old_idx]
            print(f"\n🔄 Đang so sánh: {older} ➔ {newer}...")

            # 5. RUN REPORT
            df = DataLoader.load_all_data(dates=[older, newer], base_dir=BASE_DIR_COLAB)
            
            if df.empty:
                print("❌ Không tải được dữ liệu.")
            else:
                print(f"📊 Đã tải {len(df)} dòng dữ liệu.")
                
                # Run Generators
                price_gen = PriceMatrixGenerator(df, skip_csv=True)
                price_gen.run()

                output_fn = f"Bacao_SoSanh_{older}_vs_{newer}.html"
                
                diff_gen = PromoDiffGenerator(df, price_gen, output_file=output_fn, skip_csv=True, include_all=True)
                diff_gen.run()
                
                if os.path.exists(output_fn):
                    print("\n" + "✨"*20)
                    print("🎯 TẠO BÁO CÁO THÀNH CÔNG!")
                    print(f"💾 File đã lưu: {output_fn}")
                    print("✨"*20 + "\n")
                    print("📥 Đang tự động tải báo cáo...")
                    files.download(output_fn)
                else:
                    print("✅ Không có thay đổi nào hoặc lỗi tạo file.")
        except Exception as e:
            print(f"⚠️ Có lỗi xảy ra: {e}")
