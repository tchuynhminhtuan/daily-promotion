#!/bin/bash
# ==============================================================================
# Script tự động thực thi Hybrid TGDD Pipeline theo lịch trình
# ==============================================================================

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_DIR" || exit 1

LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +"%Y-%m-%d_%H%M%S")
LOG_FILE="$LOG_DIR/hybrid_crawl_$TIMESTAMP.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 🚀 Bắt đầu quét tồn kho & Affordability TGDD..." | tee -a "$LOG_FILE"

# Ưu tiên sử dụng uv nếu có, fallback về python3
if command -v uv &> /dev/null; then
    uv run -m src.intelligence.pipeline.crawler --sync-raw 2>&1 | tee -a "$LOG_FILE"
elif [ -f "$PROJECT_DIR/.venv/bin/python" ]; then
    "$PROJECT_DIR/.venv/bin/python" -m src.intelligence.pipeline.crawler --sync-raw 2>&1 | tee -a "$LOG_FILE"
else
    python3 -m src.intelligence.pipeline.crawler --sync-raw 2>&1 | tee -a "$LOG_FILE"
fi

EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ Quét dữ liệu thành công!" | tee -a "$LOG_FILE"
    
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 📊 Đang tổng hợp báo cáo điều hành tồn kho & trợ lực tài chính (Ground-Truth Intelligence)..." | tee -a "$LOG_FILE"
    if command -v uv &> /dev/null; then
        uv run -m src.intelligence.inference.daily_inference 2>&1 | tee -a "$LOG_FILE"
    elif [ -f "$PROJECT_DIR/.venv/bin/python" ]; then
        "$PROJECT_DIR/.venv/bin/python" -m src.intelligence.inference.daily_inference 2>&1 | tee -a "$LOG_FILE"
    else
        python3 -m src.intelligence.inference.daily_inference 2>&1 | tee -a "$LOG_FILE"
    fi
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 🏁 Hoàn tất chu trình Quét & Báo cáo Tồn kho TGDD! Log: $LOG_FILE"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ❌ Có lỗi xảy ra trong bước quét dữ liệu (Exit code: $EXIT_CODE). Kiểm tra log: $LOG_FILE"
fi

exit $EXIT_CODE
