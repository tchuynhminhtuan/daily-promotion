#!/usr/bin/env bash
# ==============================================================================
# FPT MACRO SNAPSHOT CRON RUNNER
# ==============================================================================
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/../.." && pwd )"
cd "$DIR"

# Tìm python virtualenv
if [ -f "$DIR/.venv/bin/python3" ]; then
    PY="$DIR/.venv/bin/python3"
elif [ -f "$DIR/../.venv/bin/python3" ]; then
    PY="$DIR/../.venv/bin/python3"
else
    PY="python3"
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Khởi động chụp tồn kho vĩ mô..." >> "$DIR/data/snapshots/cron.log"
"$PY" "$DIR/scripts/automation/auto_macro_snapshot.py" >> "$DIR/data/snapshots/cron.log" 2>&1
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Hoàn tất!" >> "$DIR/data/snapshots/cron.log"
