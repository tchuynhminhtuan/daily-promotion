# @title 1. Cài đặt môi trường (Chạy 1 lần đầu)
# @markdown Bấm nút **Play** bên trái để cài đặt các thư viện cần thiết.
!pip install pandas
from IPython.display import clear_output
clear_output()
print("✅ Cài đặt hoàn tất! Bạn có thể chuyển sang Bước 2.")

# --- SECTION SPLIT ---

# @title 2. Tải dữ liệu từ GitHub
# @markdown Chạy ô này để tải toàn bộ dữ liệu CSV mới nhất từ GitHub.
import os

# Xóa folder cũ nếu có để đảm bảo lấy dữ liệu mới nhất
if os.path.exists('daily-promotion'):
    !rm -rf daily-promotion

print("⬇️ Đang tải dữ liệu từ GitHub...")
!git clone https://github.com/tchuynhminhtuan/daily-promotion.git

BASE_DIR_DRIVE = "/content/daily-promotion/content"

if os.path.exists(BASE_DIR_DRIVE):
    print(f"✅ Đã tải xong! Thư mục dữ liệu: {BASE_DIR_DRIVE}")
else:
    print(f"❌ Lỗi: Không tìm thấy thư mục {BASE_DIR_DRIVE}")

# --- SECTION SPLIT ---

# @title 3. Chọn ngày và Tạo báo cáo
# @markdown Chạy ô này để bắt đầu quá trình tạo báo cáo tương tác.

import os
from google.colab import files

# Thiết lập biến môi trường để script biết đọc dữ liệu từ đâu
# (Biến BASE_DIR_DRIVE đã được định nghĩa ở Bước 2)
os.environ['DAILY_PROMOTION_BASE_DIR'] = BASE_DIR_DRIVE

# Chạy script tương tác từ repository đã clone
# Script này sử dụng input() nên sẽ tương thích tốt với Colab
!python3 "/content/daily-promotion/code/generate_report_interactive.py"

# Tự động tìm file HTML vừa tạo để tải xuống
# Script interactive lưu output vào folder docs/index.html của repo
try:
    report_path = "/content/daily-promotion/docs/index.html"
    
    if os.path.exists(report_path):
        print(f"✅ Tìm thấy báo cáo tại: {report_path}")
        print("📥 Đang tải xuống...")
        files.download(report_path)
    else:
        print("⚠️ Không tìm thấy file báo cáo. Có thể quá trình tạo bị hủy hoặc file chưa được lưu.")
except Exception as e:
    print(f"Lỗi khi tải xuống: {e}")
