#!/usr/bin/env python3
"""
FPT Macro Inventory Snapshot Automation
=======================================
Tự động chụp nhanh (Fast Snapshot ~9.6s) toàn bộ tồn kho hệ sinh thái Apple
trên toàn quốc (kho tổng FPT Retail) theo các mốc thời gian:
- 07:00 (Đầu ngày - Ghi nhận hàng nhập đêm)
- 12:00 (Giữa ngày - Chốt ca sáng)
- 21:00 (Cuối ngày - Chốt ca tối & tổng kết 24h)

Mỗi lần chạy sẽ:
1. Thực thi FAST MODE crawler thu thập 482 SKU Apple.
2. Lưu snapshot vào data/snapshots/fast_YYYY-MM-DD_HH-MM.json.
3. Tự động gọi Engine phân tích Delta để so sánh biến động với snapshot liền trước.
"""

import os
import sys
import json
import time
import shutil
import subprocess
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import RAW_DATA_DIR

SNAPSHOT_DIR = os.path.join(PROJECT_ROOT, "data", "snapshots")
os.makedirs(SNAPSHOT_DIR, exist_ok=True)


def take_macro_snapshot():
    now = datetime.now()
    timestamp_str = now.strftime("%Y-%m-%d_%H-%M")
    snapshot_filename = f"fast_{timestamp_str}.json"
    snapshot_path = os.path.join(SNAPSHOT_DIR, snapshot_filename)
    latest_snapshot_path = os.path.join(SNAPSHOT_DIR, "fast_latest.json")

    print("=" * 80)
    print(f"⚡ FPT MACRO INVENTORY SNAPSHOT RUNNER - [{now.strftime('%Y-%m-%d %H:%M:%S')}]")
    print("=" * 80)

    # 1. Thực thi Fast Mode Crawler
    start_time = time.time()
    from src.pipeline.crawler import run_pipeline
    csv_path, json_path = run_pipeline(max_workers=10, mode="fast")

    if not json_path or not os.path.exists(json_path):
        print("❌ Lỗi: Không thể tạo file snapshot JSON từ crawler.")
        return None

    # 2. Đọc và lưu trữ snapshot gọn nhẹ có timestamp
    with open(json_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    # Đóng gói dữ liệu tối ưu kích thước
    snapshot_payload = {
        "timestamp": now.isoformat(),
        "recorded_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "total_skus": len(records),
        "total_units": sum(r.get("total_inventory_quantity", 0) for r in records),
        "products": [
            {
                "sku": r.get("sku_code"),
                "name": r.get("sku_name"),
                "category": r.get("category"),
                "price": r.get("price", 0),
                "qty": r.get("total_inventory_quantity", 0)
            }
            for r in records
        ]
    }

    with open(snapshot_path, "w", encoding="utf-8") as f:
        json.dump(snapshot_payload, f, ensure_ascii=False, indent=2)

    # Cập nhật latest symlink/copy
    shutil.copyfile(snapshot_path, latest_snapshot_path)

    elapsed = time.time() - start_time
    print(f"\n✅ Đã lưu snapshot thành công trong {elapsed:.1f}s:")
    print(f"   📁 Snapshot: {snapshot_path}")
    print(f"   📦 Tổng SKU: {snapshot_payload['total_skus']} | Tổng máy toàn quốc: {snapshot_payload['total_units']:,} máy")

    # 3. Tự động kích hoạt Engine so sánh Delta nếu có từ 2 snapshot trở lên
    try:
        analyzer_script = os.path.join(PROJECT_ROOT, "scripts", "analyze_macro_delta.py")
        if os.path.exists(analyzer_script):
            print("\n🔍 Đang kích hoạt Engine phân tích biến động tồn kho (Delta Analysis)...")
            subprocess.run([sys.executable, analyzer_script], check=False)
    except Exception as e:
        print(f"⚠️ Không thể tự động chạy delta analysis: {e}")

    return snapshot_path


if __name__ == "__main__":
    take_macro_snapshot()
