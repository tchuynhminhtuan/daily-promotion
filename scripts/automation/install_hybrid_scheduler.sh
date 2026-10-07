#!/bin/bash
# ==============================================================================
# Cài đặt lịch trình tự động quét TGDD 3 lần/ngày trên macOS (LaunchAgent)
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_NAME="com.brucehuynh.hybrid_tgdd.plist"
PLIST_PATH="$SCRIPT_DIR/$PLIST_NAME"
TARGET_DIR="$HOME/Library/LaunchAgents"

if [ ! -f "$PLIST_PATH" ]; then
    echo "❌ Lỗi: Không tìm thấy $PLIST_NAME tại $SCRIPT_DIR"
    exit 1
fi

mkdir -p "$TARGET_DIR"

echo "⚙️ Đang cài đặt lịch trình quét TGDD 3 lần/ngày (07:00, 14:00, 22:30)..."

# 1. Hủy lịch trình cũ nếu có
launchctl unload "$TARGET_DIR/$PLIST_NAME" 2>/dev/null

# 2. Cấp quyền thực thi cho script runner
chmod +x "$SCRIPT_DIR/run_hybrid_tgdd.sh"

# 3. Sao chép file plist vào LaunchAgents
cp "$PLIST_PATH" "$TARGET_DIR/"

# 4. Kích hoạt LaunchAgent mới
launchctl load "$TARGET_DIR/$PLIST_NAME"

echo "✅ Cài đặt thành công!"
echo "⏰ Hệ thống sẽ tự động chạy 3 lần mỗi ngày:"
echo "   - 07:00 Sáng (Tồn kho & giá mở cửa)"
echo "   - 14:00 Chiều (Giữa ngày)"
echo "   - 22:30 Tối   (Chốt sổ đóng cửa)"
echo "📁 Dữ liệu sẽ lưu riêng biệt theo giờ: data/hybrid/tgdd_inventory_YYYY-MM-DD_HHMM.csv"
echo "📝 Log hệ thống theo dõi tại: /tmp/tgdd_hybrid_scrape.out"
