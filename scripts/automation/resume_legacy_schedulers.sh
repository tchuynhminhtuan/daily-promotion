#!/bin/bash
# ==============================================================================
# Khôi phục lại các bộ lập lịch tự động cũ (Apple Playwright Scraper & Marshall)
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="$HOME/Library/LaunchAgents"

echo "▶️  Đang khôi phục lại các bộ lập lịch cũ..."

# 1. Cài đặt lại LaunchAgents
if [ -f "$SCRIPT_DIR/com.brucehuynh.dailyscrape.plist" ]; then
    cp "$SCRIPT_DIR/com.brucehuynh.dailyscrape.plist" "$TARGET_DIR/"
    launchctl load "$TARGET_DIR/com.brucehuynh.dailyscrape.plist" 2>/dev/null
    echo "  ✓ Đã kích hoạt lại LaunchAgent: com.brucehuynh.dailyscrape"
fi

if [ -f "$SCRIPT_DIR/com.brucehuynh.marshall_daily.plist" ]; then
    cp "$SCRIPT_DIR/com.brucehuynh.marshall_daily.plist" "$TARGET_DIR/"
    launchctl load "$TARGET_DIR/com.brucehuynh.marshall_daily.plist" 2>/dev/null
    echo "  ✓ Đã kích hoạt lại LaunchAgent: com.brucehuynh.marshall_daily"
fi

# 2. Mở comment trong Crontab
CURRENT_CRON=$(crontab -l 2>/dev/null)
if [ -n "$CURRENT_CRON" ]; then
    NEW_CRON=$(echo "$CURRENT_CRON" | sed -E 's|^#[[:space:]]*\[PAUSED\][[:space:]]*(.*1_core_workflow\.sh.*)|\1|g' | sed -E 's|^#[[:space:]]*\[PAUSED\][[:space:]]*(.*1b_marshall_workflow\.sh.*)|\1|g')
    echo "$NEW_CRON" | crontab -
    echo "  ✓ Đã khôi phục các dòng trong crontab"
fi

echo "✅ Hoàn tất khôi phục!"
