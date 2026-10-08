#!/usr/bin/env bash
# ==============================================================================
# FPT INVENTORY INTELLIGENCE - AUTOMATED EXECUTION RUNNER
# ==============================================================================
set -e

# Tự động định vị thư mục gốc của dự án fpt-inventory-intelligence
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/../.." && pwd )"
cd "$DIR"

echo "================================================================================"
echo "🚀 KHỞI ĐỘNG FPT INVENTORY INTELLIGENCE PIPELINE"
echo "Thư mục làm việc: $DIR"
echo "Thời gian: $(date '+%Y-%m-%d %H:%M:%S')"
echo "================================================================================"

# Tự động phát hiện python trong virtual environment
if [ -f "$DIR/.venv/bin/python3" ]; then
    PY="$DIR/.venv/bin/python3"
elif [ -f "$DIR/venv/bin/python3" ]; then
    PY="$DIR/venv/bin/python3"
elif [ -f "$DIR/../.venv/bin/python3" ]; then
    PY="$DIR/../.venv/bin/python3"
else
    PY="python3"
fi

echo "Sử dụng Python runtime: $PY"

# 1. Chạy Crawler thu thập tồn kho thực tế
echo ""
echo "📡 BƯỚC 1: Thu thập tồn kho trực tiếp từ FPT Gateway API..."
"$PY" src/pipeline/crawler.py --workers 12

# 2. Chạy Inference Engine tổng hợp báo cáo điều hành
echo ""
echo "📊 BƯỚC 2: Phân tích chỉ số điều hành & lập báo cáo..."
"$PY" src/inference/daily_inference.py

echo ""
echo "================================================================================"
echo "✅ HOÀN TẤT CHU TRÌNH ĐIỀU HÀNH FPT INVENTORY INTELLIGENCE!"
echo "Báo cáo mới nhất: $DIR/data/reports/daily_report_latest.md"
echo "================================================================================"
