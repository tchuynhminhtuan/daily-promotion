#!/usr/bin/env python3
"""
[01] Sync Master Provinces & ERP Locations from Viettel Gateway
================================================================
Fetches official administrative provinces from Viettel Store Microservice
Gateway (/profile/v1/province/load) and stores them in data/master/.
"""

import json
import logging
from pathlib import Path
import sys

# Add project root to sys.path
PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_DIR))
import config
from src.client import ViettelStoreClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SyncProvinces")


def main():
    print("=" * 80)
    print("🚀 [BƯỚC 01] ĐỒNG BỘ DANH MỤC 63 TỈNH THÀNH & MÃ ERP TỪ VIETTEL STORE GATEWAY")
    print("=" * 80)

    client = ViettelStoreClient()
    provinces = client.get_master_provinces()

    if not provinces:
        print("❌ Không lấy được danh sách tỉnh thành từ Viettel Gateway!")
        return

    print(f"✅ Đã tải thành công {len(provinces)} tỉnh/thành phố chuẩn hóa!")

    # Format data
    data = [
        {
            "province_id": p.province_id,
            "province_code": p.province_code,
            "province_name": p.province_name,
            "erp_province_id": p.erp_province_id,
            "status": p.status,
        }
        for p in provinces
    ]

    out_file = config.MASTER_DIR / "viettel_master_provinces.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"📁 Đã lưu master data tại: {out_file}\n")
    print(f"{'ID':<6} | {'Code':<6} | {'ERP ID':<8} | {'Tên Tỉnh / Thành Phố'}")
    print("-" * 55)
    for p in provinces[:15]:
        print(f"{p.province_id:<6} | {p.province_code:<6} | {p.erp_province_id:<8} | {p.province_name}")
    if len(provinces) > 15:
        print(f"... và {len(provinces) - 15} tỉnh thành khác.")
    print("=" * 80)


if __name__ == "__main__":
    main()
