#!/bin/bash
# ==============================================================================
# Tạm dừng các bộ lập lịch tự động cũ (Apple Playwright Scraper & Marshall)
# ==============================================================================

echo "⏸️  Đang tạm dừng các bộ lập lịch cũ..."

# 1. Unload & gỡ khỏi LaunchAgents (macOS background daemon)
TARGET_DIR="$HOME/Library/LaunchAgents"

if [ -f "$TARGET_DIR/com.brucehuynh.dailyscrape.plist" ]; then
    launchctl unload "$TARGET_DIR/com.brucehuynh.dailyscrape.plist" 2>/dev/null
    rm -f "$TARGET_DIR/com.brucehuynh.dailyscrape.plist"
    echo "  ✓ Đã gỡ bỏ LaunchAgent: com.brucehuynh.dailyscrape"
fi

if [ -f "$TARGET_DIR/com.brucehuynh.marshall_daily.plist" ]; then
    launchctl unload "$TARGET_DIR/com.brucehuynh.marshall_daily.plist" 2>/dev/null
    rm -f "$TARGET_DIR/com.brucehuynh.marshall_daily.plist"
    echo "  ✓ Đã gỡ bỏ LaunchAgent: com.brucehuynh.marshall_daily"
fi

# 2. Vô hiệu hóa (comment out) các dòng tương ứng trong Crontab
CURRENT_CRON=$(crontab -l 2>/dev/null)
if [ -n "$CURRENT_CRON" ]; then
    # Comment out các dòng chứa 1_core_workflow.sh và 1b_marshall_workflow.sh
    NEW_CRON=$(echo "$CURRENT_CRON" | sed -E 's|^([^#].*1_core_workflow\.sh.*)|# [PAUSED] \1|g' | sed -E 's|^([^#].*1b_marshall_workflow\.sh.*)|# [PAUSED] \1|g')
    echo "$NEW_CRON" | crontab -
    echo "  ✓ Đã comment out các tác vụ cũ trong crontab"
fi

echo "✅ Hoàn tất! Hệ thống Hybrid TGDD (com.brucehuynh.hybrid_tgdd) vẫn hoạt động bình thường."
