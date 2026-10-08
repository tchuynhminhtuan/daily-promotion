"""
FPT Master Store Geospatial & Channel Mapper
============================================
Thống kê mạng lưới 602 siêu thị FPT Shop & F.Studio by FPT toàn quốc:
- Phân bổ theo 34 mã tỉnh thành GSO
- Phân loại kênh FPT Shop vs F.Studio
- Kiểm tra tỷ lệ phủ tọa độ GPS (Latitude/Longitude)
"""

import os
import sys
from collections import Counter

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import KEY_PROVINCES
from src.pipeline.store_master import FPTStoreMasterRegistry


def main():
    registry = FPTStoreMasterRegistry()
    stores = registry.stores_list

    total_stores = len(stores)
    fpt_count = sum(1 for s in stores if s.get("channel") == "FPT Shop")
    fstudio_count = sum(1 for s in stores if s.get("channel") == "F.Studio by FPT")
    gps_count = sum(1 for s in stores if s.get("latitude") and s.get("longitude"))
    legacy_count = sum(1 for s in stores if s.get("legacyAddress"))
    cluster_mapped_count = sum(1 for s in stores if s.get("store_code"))

    province_counter = Counter(s.get("provinceCode") for s in stores)

    print("=" * 80)
    print("📍 BÁO CÁO MẠNG LƯỚI PHÂN PHỐI FPT RETAIL & F.STUDIO")
    print("=" * 80)
    print(f"Tổng số siêu thị hoạt động : {total_stores}")
    print(f"  • Chuỗi FPT Shop          : {fpt_count} shop ({fpt_count*100//total_stores}%)")
    print(f"  • Chuỗi F.Studio by FPT   : {fstudio_count} shop ({fstudio_count*100//total_stores}%)")
    print(f"  • Có tọa độ GPS chuẩn xác : {gps_count}/{total_stores} ({gps_count*100//total_stores}%)")
    print(f"  • Có địa chỉ cũ (pre-merger): {legacy_count}/{total_stores} ({legacy_count*100//total_stores}%)")
    print(f"  • Đã khớp cây nhân sự (Tree): {cluster_mapped_count}/{total_stores} (Độ phủ: {cluster_mapped_count*100//269}% trên 269 shop tree)")
    print("-" * 80)
    print("TOP TỈNH THÀNH CÓ SỐ LƯỢNG SIÊU THỊ LỚN NHẤT:")
    print(f"{'Mã GSO':<8} | {'Tên Tỉnh / Thành':<22} | {'Số Siêu Thị':<12} | {'Tỷ Lệ':<8}")
    print("-" * 60)

    for p_code, count in province_counter.most_common(12):
        p_name = KEY_PROVINCES.get(p_code, f"Tỉnh mã {p_code}")
        pct = f"{count*100/total_stores:.1f}%"
        print(f"{p_code:<8} | {p_name:<22} | {count:<12} | {pct:<8}")

    print("=" * 80)


if __name__ == "__main__":
    main()
