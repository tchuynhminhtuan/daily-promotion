#!/bin/bash
# ==============================================================================
# Script mở Terminal hiển thị toàn bộ quá trình Quét + Dự báo AI/ML
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_DIR" || exit 1

# Đổi tiêu đề cửa sổ Terminal
echo -n -e "\033]0;🧠 TGDD Retail Intelligence & AI Forecasting\007"

clear
echo "================================================================================="
echo "🚀 ĐANG KÍCH HOẠT QUÉT TỒN KHO & CHẠY DỰ BÁO AI/ML HÀNG NGÀY"
echo "Thời gian: $(date '+%Y-%m-%d %H:%M:%S')"
echo "================================================================================="
echo ""

# Chạy runner
"$SCRIPT_DIR/run_hybrid_tgdd.sh"
RUN_STATUS=$?

echo ""
echo "================================================================================="
if [ $RUN_STATUS -eq 0 ]; then
    echo "🎉 HOÀN TẤT THÀNH CÔNG! Dữ liệu & kết quả AI đã được cập nhật."
    # Bắn thông báo macOS Banner ra màn hình desktop
    osascript -e 'display notification "Đã cập nhật dự báo AI & Tồn kho TGDD thành công!" with title "🧠 TGDD Retail Intelligence" sound name "Glass"' 2>/dev/null
else
    echo "❌ CÓ LỖI XẢY RA TRONG QUÁ TRÌNH THỰC THI. Kiểm tra log phía trên."
    osascript -e 'display notification "Có lỗi khi chạy dự báo TGDD. Kiểm tra Terminal!" with title "⚠️ TGDD Retail Intelligence" sound name "Basso"' 2>/dev/null
fi
echo "================================================================================="
echo ""
echo "💡 Nhấn phím bất kỳ (hoặc click đóng cửa sổ Terminal) khi bạn đã xem xong kết quả..."
read -n 1 -s
exit $RUN_STATUS
