"""
FPT Cluster Personnel Tree & Master Store Mapper
================================================
Khớp nối dữ liệu danh bạ nhân sự / quản lý vùng (cluster_personnel_tree.json)
với sổ cái 602 siêu thị FPT Shop & F.Studio (fpt_master_stores.json):

1. Trích xuất toàn bộ 270 cửa hàng FPT từ cây phân cấp nhân sự.
2. Khớp nối độ chính xác cao theo địa chỉ, tên shop, số nhà, tỉnh thành.
3. Làm giàu fpt_master_stores.json với các trường:
   - store_code (mã nhân sự nội bộ, ví dụ: '3958531')
   - store_name (tên quản lý vùng, ví dụ: 'F-Studio By Fpt @ 53 Nguyen Tat Thanh')
   - cluster_group (Nhóm cụm A, B, C, D)
   - asm_group (Cụm ASM quản lý)
   - store_id (ID hệ thống)
   - store_size (Diện tích cửa hàng)
   - manager (Danh sách quản lý)
   - expert (Danh sách chuyên viên tư vấn)
4. Xuất file tra cứu hai chiều: data/master/store_code_mapping.json
"""

import os
import sys
import json
import re
from typing import Dict, Any, List

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import MASTER_DIR, MASTER_STORES_FILE
from src.pipeline.store_master import clean_address_text

CLUSTER_FILE = os.path.join(MASTER_DIR, "cluster_personnel_tree.json")
MAPPING_FILE = os.path.join(MASTER_DIR, "store_code_mapping.json")


def extract_features(text: str):
    clean = clean_address_text(text)
    numbers = set(re.findall(r'\b\d+[a-zA-Z]?\b', clean))
    tokens = set([w for w in clean.split() if len(w) > 1 and w not in [
        'fpt', 'shop', 'studio', 'duong', 'phuong', 'quan', 'tinh', 'thanh', 'pho', 'so', 'khu', 'thi', 'tran', 'by', 'at'
    ]])
    return clean, numbers, tokens


def main():
    if not os.path.exists(CLUSTER_FILE):
        print(f"❌ Không tìm thấy file cây nhân sự: {CLUSTER_FILE}")
        return

    if not os.path.exists(MASTER_STORES_FILE):
        print(f"❌ Không tìm thấy file Master Stores: {MASTER_STORES_FILE}")
        return

    print("=" * 80)
    print("🔄 KHỞI ĐỘNG MAPPER: CÂY NHÂN SỰ ➡️ MASTER STORES FPT")
    print("=" * 80)

    with open(CLUSTER_FILE, "r", encoding="utf-8") as f:
        tree_data = json.load(f)

    with open(MASTER_STORES_FILE, "r", encoding="utf-8") as f:
        master_stores: List[Dict[str, Any]] = json.load(f)

    # 1. Trích xuất cửa hàng FPT từ cây nhân sự
    tree_fpt_stores: Dict[str, Dict[str, Any]] = {}

    def extract_stores(obj, cluster='', asm=''):
        if isinstance(obj, dict):
            c, a = cluster, asm
            for k, v in obj.items():
                if k in ['A', 'B', 'C', 'D', 'Management']:
                    c = k
                if 'ASM' in k or 'asm' in k.lower():
                    a = k
                if k == 'stores_detail' and isinstance(v, list):
                    for s in v:
                        if s.get('chanel_code') == 'FPT':
                            sc = str(s.get('store_code', '')).strip()
                            if sc and sc not in tree_fpt_stores:
                                item = dict(s)
                                item['cluster_group'] = c
                                item['asm_group'] = a
                                tree_fpt_stores[sc] = item
                else:
                    extract_stores(v, c, a)
        elif isinstance(obj, list):
            for item in obj:
                extract_stores(item, cluster, asm)

    extract_stores(tree_data)
    print(f"🌲 Đã trích xuất {len(tree_fpt_stores)} cửa hàng FPT từ cây nhân sự.")
    print(f"🏢 Tổng số siêu thị Master Stores FPT hiện có: {len(master_stores)}")

    # Bản đồ viết tắt tỉnh thành
    prov_aliases = {
        'bnh': 'bac ninh', 'bac ninh': 'bac ninh',
        'dlk': 'dak lak', 'dak lak': 'dak lak', 'buon ma thuot': 'dak lak',
        'hni': 'ha noi', 'ha noi': 'ha noi',
        'hcm': 'ho chi minh', 'ho chi minh': 'ho chi minh', 'sai gon': 'ho chi minh',
        'dng': 'da nang', 'da nang': 'da nang',
        'hpg': 'hai phong', 'hai phong': 'hai phong',
        'nan': 'nghe an', 'nghe an': 'nghe an', 'vinh': 'nghe an',
        'tha': 'thanh hoa', 'thanh hoa': 'thanh hoa',
        'qnh': 'quang ninh', 'quang ninh': 'quang ninh',
        'tbh': 'thai binh', 'thai binh': 'thai binh',
        'hth': 'ha tinh', 'ha tinh': 'ha tinh',
        'bdg': 'binh duong', 'binh duong': 'binh duong',
        'dni': 'dong nai', 'dong nai': 'dong nai',
        'btn': 'binh thuan', 'binh thuan': 'binh thuan',
        'ntn': 'ninh thuan', 'ninh thuan': 'ninh thuan',
        'kha': 'khanh hoa', 'khanh hoa': 'khanh hoa', 'nha trang': 'khanh hoa',
        'hdg': 'hai duong', 'hai duong': 'hai duong',
        'bgg': 'bac giang', 'bac giang': 'bac giang',
        'pyn': 'phu yen', 'phu yen': 'phu yen',
        'ktm': 'kon tum', 'kon tum': 'kon tum',
        'bdh': 'binh dinh', 'binh dinh': 'binh dinh',
        'tnh': 'tay ninh', 'tay ninh': 'tay ninh',
        'kgg': 'kien giang', 'kien giang': 'kien giang'
    }

    # 2. Khớp nối và ghi nhận mapping
    matched_count = 0
    code_mapping = {}  # store_code -> shopCode & shopCode -> store_code

    master_by_shopcode = {s["shopCode"]: s for s in master_stores}

    for sc, ts in tree_fpt_stores.items():
        t_name = ts.get('store_name', '')
        t_raw = ts.get('store_address_raw', '')
        t_addr = ts.get('store_address', '')
        t_prov = ts.get('store_province', '')

        clean_t_all, t_numbers, t_tokens = extract_features(f'{t_name} {t_raw} {t_addr}')

        best_ms = None
        best_score = 0

        for ms in master_stores:
            m_code = ms.get('shopCode')
            m_name = ms.get('shopName', '')
            m_disp = ms.get('displayAddress', '')
            m_leg = ms.get('legacyAddress', '')

            clean_m_all, m_numbers, m_tokens = extract_features(f'{m_name} {m_disp} {m_leg}')

            score = 0

            # Khớp số nhà (trọng số cao nhất)
            common_num = t_numbers & m_numbers
            if common_num:
                score += len(common_num) * 20

            # Khớp từ khóa tên đường / quận
            common_tokens = t_tokens & m_tokens
            score += len(common_tokens) * 3

            # Khớp tỉnh thành
            for k, v in prov_aliases.items():
                if (k in clean_t_all or k in clean_address_text(t_prov)) and (v in clean_m_all or k in clean_m_all):
                    score += 12
                    break

            # Phân loại chuyên biệt: Garmin Brand Agency vs FPT Shop / F.Studio
            is_garmin_shop = (
                "garmin" in m_name.lower() or 
                " g-" in m_name.lower() or 
                m_name.startswith("G-") or
                "(garmin store" in m_disp.lower() or
                any(f.get("name") == "Garmin" for f in ms.get("shopFeatures", []))
            )
            is_fpt_or_fstudio = (
                any(f.get("name") in ["FPTShop", "Điện máy", "Trung Tâm Laptop", "F Studio Side by side", "F.Studio"] for f in ms.get("shopFeatures", [])) or
                "fpt shop" in m_name.lower() or "f.studio" in m_name.lower()
            )

            # Nếu cửa hàng từ cây nhân sự là kênh FPT/Apple nhưng shop ứng viên là Garmin: PHẠT NẶNG
            tree_is_garmin = "garmin" in t_name.lower()
            if is_garmin_shop and not tree_is_garmin:
                score -= 100  # Loại bỏ hoàn toàn quầy Garmin chuyên biệt khỏi điểm bán Apple/FPT

            if is_fpt_or_fstudio and not tree_is_garmin:
                score += 30   # Ưu tiên tuyệt đối shop FPT Shop / F.Studio chuẩn

            if score > best_score:
                best_score = score
                best_ms = ms

        if best_ms and best_score >= 28:
            matched_count += 1
            shop_code = best_ms["shopCode"]

            # Bổ sung các trường vào master_stores
            best_ms["store_code"] = sc
            best_ms["store_name"] = t_name
            best_ms["cluster_group"] = ts.get("cluster_group", "")
            best_ms["asm_group"] = ts.get("asm_group", "")
            best_ms["store_id"] = ts.get("store_id", "")
            best_ms["store_size"] = ts.get("store_size", "")
            best_ms["revenue"] = ts.get("revenue", "")
            best_ms["manager"] = ts.get("manager", [])
            best_ms["expert"] = ts.get("expert", [])
            best_ms["tree_address_raw"] = t_raw

            code_mapping[sc] = {
                "shopCode": shop_code,
                "shopName": best_ms.get("shopName"),
                "store_code": sc,
                "store_name": t_name,
                "cluster_group": ts.get("cluster_group", ""),
                "asm_group": ts.get("asm_group", ""),
                "displayAddress": best_ms.get("displayAddress"),
                "latitude": best_ms.get("latitude"),
                "longitude": best_ms.get("longitude")
            }

    # 3. Ghi đè cập nhật vào fpt_master_stores.json
    with open(MASTER_STORES_FILE, "w", encoding="utf-8") as f:
        json.dump(master_stores, f, ensure_ascii=False, indent=2)

    # 4. Ghi file tra cứu độc lập store_code_mapping.json
    with open(MAPPING_FILE, "w", encoding="utf-8") as f:
        json.dump(code_mapping, f, ensure_ascii=False, indent=2)

    print("-" * 80)
    print(f"✅ KHỚP NỐI THÀNH CÔNG: {matched_count}/{len(tree_fpt_stores)} ({matched_count*100//len(tree_fpt_stores)}%)")
    print(f"📦 Đã cập nhật dữ liệu vào: {MASTER_STORES_FILE}")
    print(f"📑 Đã tạo file tra cứu mã: {MAPPING_FILE}")
    print("=" * 80)

    # Hiển thị mẫu kiểm tra
    sample_code = "3958531"
    if sample_code in code_mapping:
        print(f"\n🔍 KIỂM TRA MẪU MÃ SHOP '{sample_code}':")
        print(json.dumps(code_mapping[sample_code], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
