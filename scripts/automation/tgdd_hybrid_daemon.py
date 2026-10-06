#!/usr/bin/env python3
"""
TGDD Hybrid Cross-Platform Scheduler Daemon
Tự động kích hoạt pipeline quét tồn kho & Affordability vào các khung giờ vàng trong ngày.
Mặc định: 08:30, 14:00, 22:30 hàng ngày (3 lần / ngày).
"""

import sys
import os
import time
import argparse
from datetime import datetime, timedelta

# Thêm thư mục gốc vào PYTHONPATH
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, PROJECT_ROOT)

from src.hybrid.tgdd_hybrid_pipeline import run_pipeline


def get_seconds_until_next_run(target_times: list) -> tuple:
    """
    Tính số giây còn lại cho đến mốc giờ quét tiếp theo.
    target_times: danh sách chuỗi dạng ["08:30", "14:00", "22:30"]
    """
    now = datetime.now()
    candidate_dts = []

    for t_str in target_times:
        h, m = map(int, t_str.strip().split(":"))
        dt_today = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if dt_today > now:
            candidate_dts.append(dt_today)
        else:
            # Nếu mốc giờ hôm nay đã qua thì sang ngày mai
            dt_tomorrow = dt_today + timedelta(days=1)
            candidate_dts.append(dt_tomorrow)

    next_run = min(candidate_dts)
    seconds_wait = (next_run - now).total_seconds()
    return max(1, int(seconds_wait)), next_run


def run_daemon(schedule_times: list, sync_raw: bool = True):
    print("=" * 80)
    print("⏰ KHỞI ĐỘNG TGDD HYBRID SCHEDULER DAEMON (3 LẦN / NGÀY)")
    print(f"Các mốc giờ quét hàng ngày: {', '.join(schedule_times)}")
    print(f"Thư mục làm việc: {PROJECT_ROOT}")
    print("Nhấn Ctrl + C để dừng daemon bất kỳ lúc nào.")
    print("=" * 80)

    while True:
        wait_sec, next_dt = get_seconds_until_next_run(schedule_times)
        hours = wait_sec // 3600
        mins = (wait_sec % 3600) // 60
        secs = wait_sec % 60
        
        print(f"\n[DAEMON] ⏳ Mốc quét tiếp theo: {next_dt.strftime('%Y-%m-%d %H:%M:%S')} (còn {hours}h {mins}m {secs}s)")
        
        try:
            # Ngủ chờ đến giờ
            time.sleep(wait_sec)
        except KeyboardInterrupt:
            print("\n🛑 Đã nhận tín hiệu dừng từ người dùng. Thoát Daemon.")
            break

        print(f"\n[DAEMON] 🚀 Đến giờ quét ({datetime.now().strftime('%H:%M:%S')})! Bắt đầu thực thi pipeline...")
        try:
            csv_path, json_path = run_pipeline(sync_raw=sync_raw, max_workers=12)
            print(f"[DAEMON] ✅ Hoàn tất lượt quét lúc {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"         📁 CSV:  {csv_path}")
            print(f"         📁 JSON: {json_path}")
        except Exception as e:
            print(f"[DAEMON] ❌ Có lỗi xảy ra trong quá trình quét: {e}")

        # Nghỉ ngắn 2 giây để tránh bị gọi lặp lại trong cùng 1 giây
        time.sleep(2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TGDD Hybrid Scheduler Daemon")
    parser.add_argument(
        "--times",
        default="08:30,14:00,22:30",
        help="Các mốc giờ quét hàng ngày, phân tách bằng dấu phẩy (Mặc định: '08:30,14:00,22:30')"
    )
    parser.add_argument(
        "--sync-raw",
        action="store_true",
        default=True,
        help="Đồng bộ sang thư mục data/raw/ hàng ngày"
    )
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="Chạy ngay 1 lượt quét trước khi vào chu kỳ ngủ"
    )

    args = parser.parse_args()
    times_list = [t.strip() for t in args.times.split(",") if t.strip()]

    if args.run_now:
        print("⚡ Đang thực thi ngay 1 lượt quét đầu tiên...")
        run_pipeline(sync_raw=args.sync_raw, max_workers=12)

    run_daemon(times_list, sync_raw=args.sync_raw)
