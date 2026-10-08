#!/usr/bin/env python3
"""
FPT Macro Inventory Background Scheduler Daemon
================================================
Daemon chạy nền tự động chụp snapshot tồn kho vĩ mô vào 3 mốc:
- 07:00: Nhập hàng đêm / Mở ngày
- 12:00: Ca sáng / Giữa ngày
- 21:00: Ca tối / Chốt ngày

Có thể chạy trực tiếp:
  python3 scripts/automation/scheduler_macro_daemon.py
Hoặc chạy background:
  nohup python3 scripts/automation/scheduler_macro_daemon.py > data/snapshots/daemon.log 2>&1 &
"""

import os
import sys
import time
import subprocess
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

SNAPSHOT_SCRIPT = os.path.join(PROJECT_ROOT, "scripts", "automation", "auto_macro_snapshot.py")
SCHEDULE_TIMES = ["07:00", "12:00", "21:00"]


def run_job():
    print(f"\n⏰ [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Kích hoạt chụp snapshot định kỳ...")
    try:
        subprocess.run([sys.executable, SNAPSHOT_SCRIPT], check=False)
    except Exception as e:
        print(f"❌ Lỗi khi thực thi job: {e}")


def main():
    print("=" * 80)
    print("🚀 KHỞI ĐỘNG FPT MACRO INVENTORY SCHEDULER DAEMON")
    print(f"⏰ Lịch chạy tự động mỗi ngày: {', '.join(SCHEDULE_TIMES)}")
    print("Thư mục dự án:", PROJECT_ROOT)
    print("Nhấn Ctrl+C để dừng daemon.")
    print("=" * 80)

    last_run_minute = None

    while True:
        now = datetime.now()
        current_hm = now.strftime("%H:%M")

        if current_hm in SCHEDULE_TIMES and current_hm != last_run_minute:
            last_run_minute = current_hm
            run_job()

        # Ngủ 20s kiểm tra 1 lần
        time.sleep(20)


if __name__ == "__main__":
    main()
