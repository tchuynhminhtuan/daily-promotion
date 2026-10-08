"""
FPT Store Inventory Inspector
=============================
Công cụ tra cứu nhanh thông tin siêu thị và kiểm tra tình trạng hàng hóa:
1. Tìm kiếm siêu thị theo Shop Code, tên đường hoặc địa chỉ cũ/mới.
2. Tra cứu danh sách các mặt hàng đang có sẵn tại một siêu thị cụ thể.
"""

import os
import sys
import json
import argparse
from typing import Optional

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import RAW_DATA_DIR
from src.pipeline.store_master import FPTStoreMasterRegistry


def check_store(shop_query: str, sku_code: Optional[str] = None, probe: bool = False):
    registry = FPTStoreMasterRegistry()
    matched_shops = registry.search_by_query(shop_query, limit=5)

    if not matched_shops:
        print(f"❌ Không tìm thấy siêu thị FPT nào khớp với từ khóa: '{shop_query}'")
        return

    print("=" * 80)
    print(f"🏬 TÌM THẤY {len(matched_shops)} SIÊU THỊ PHÙ HỢP:")
    print("=" * 80)
    for s in matched_shops:
        sc = s.get("shopCode")
        name = s.get("shopName")
        ch = s.get("channel")
        addr = s.get("displayAddress")
        old_addr = s.get("legacyAddress", "")
        lat = s.get("latitude")
        lng = s.get("longitude")
        open_t = s.get("timeOpen")
        close_t = s.get("timeClose")

        print(f"\n[Mã Shop: {sc}] - {name} ({ch})")
        tree_code = s.get("store_code")
        tree_name = s.get("store_name")
        cluster_g = s.get("cluster_group")
        asm_g = s.get("asm_group")
        if tree_code:
            print(f"  🏢 Cụm Quản Lý     : Nhóm {cluster_g} | Cụm ASM: {asm_g or 'N/A'}")
            print(f"  🏷️  Mã Nhân Sự (Tree): {tree_code} ({tree_name})")
        print(f"  📍 Địa chỉ hiện tại : {addr}")
        if old_addr:
            print(f"  🔄 Địa chỉ cũ      : {old_addr}")
        print(f"  🌐 Tọa độ GPS       : {lat}, {lng}")
        print(f"  ⏰ Giờ mở cửa       : {open_t} - {close_t}")

    # Đọc snapshot tồn kho mới nhất nếu có
    snapshot_file = os.path.join(RAW_DATA_DIR, "fpt_inventory_deep_latest.json")
    if not os.path.exists(snapshot_file):
        print("\n⚠️ Chưa có file snapshot tồn kho fpt_inventory_deep_latest.json để tra cứu sản phẩm.")
        print("💡 Hãy chạy crawler trước: python3 src/pipeline/crawler.py")
        return

    target_shop_code = str(matched_shops[0]["shopCode"])
    print("\n" + "-" * 80)
    print(f"📦 KIỂM TRA MẶT HÀNG CÒN SẴN TẠI SHOP {target_shop_code} ({matched_shops[0]['shopName']}):")
    print("-" * 80)

    with open(snapshot_file, "r", encoding="utf-8") as f:
        products = json.load(f)

    available_items = []
    for p in products:
        p_sku = p.get("sku_code")
        if sku_code and p_sku != sku_code:
            continue

        # Kiểm tra shop có trong fpt_store_list hoặc fstudio_store_list
        in_fpt = any(str(s.get("shopCode")) == target_shop_code for s in p.get("fpt_store_list", []))
        in_fstudio = any(str(s.get("shopCode")) == target_shop_code for s in p.get("fstudio_store_list", []))

        if in_fpt or in_fstudio:
            available_items.append(p)

    if not available_items:
        print(f"  ⚠️ Hiện tại không ghi nhận sản phẩm nào (hoặc SKU {sku_code}) còn tại shop này trong snapshot gần nhất.")
    else:
        print(f"  ✅ Có {len(available_items)} biến thể Apple sẵn sàng giao ngay tại siêu thị này:")
        
        # Nếu bật --probe hoặc mặc định: dò chính xác số lượng máy
        if probe:
            print("  🔍 Đang kiểm tra số lượng máy thực tế từng biến thể tại quầy...")
            from config import PICKUP_API_URL, HEADERS_FPTSHOP, HEADERS_FSTUDIO
            import requests

            total_units = 0
            p_code = matched_shops[0].get("provinceCode", "79")

            for item in available_items:
                i_sku = item.get("sku_code")
                i_name = item.get("sku_name")
                i_price = item.get("price", 10000000)
                
                # Xác định kênh
                in_fstudio = any(str(s.get("shopCode")) == target_shop_code for s in item.get("fstudio_store_list", []))
                headers = HEADERS_FSTUDIO if in_fstudio else HEADERS_FPTSHOP
                ch_label = "F.Studio" if in_fstudio else "FPT Shop"

                qty_on_hand = 0
                for test_q in range(1, 10):
                    payload = {
                        "cityCode": p_code,
                        "orderDoctotal": i_price * test_q,
                        "product": [{"id": i_sku, "name": i_name, "quantity": test_q, "price": i_price, "unit": 8, "isCheckInventory": True}]
                    }
                    try:
                        r = requests.post(PICKUP_API_URL, headers=headers, json=payload, timeout=3)
                        shops_res = r.json().get("data", [])
                        match = any(str(s.get("shopCode")) == target_shop_code and s.get("pickupType") == 0 for s in shops_res)
                        if match:
                            qty_on_hand = test_q
                        else:
                            break
                    except Exception:
                        break

                total_units += qty_on_hand
                price_str = f"{i_price:,.0f} đ".replace(",", ".")
                print(f"   • [{i_sku}] {i_name[:40]:<40} ({ch_label:<7}) | Có sẵn: {qty_on_hand:2d} máy | Giá: {price_str}")

            print("-" * 80)
            print(f"  🎯 TỔNG CỘNG SỐ MÁY APPLE VẬT LÝ CÓ SẴN TẠI QUẦY: {total_units} MÁY")
            print("-" * 80)
        else:
            for item in available_items[:20]:
                price_str = f"{item.get('price', 0):,.0f} đ".replace(",", ".")
                print(f"   • [{item.get('sku_code')}] {item.get('sku_name')[:45]:<45} | Giá: {price_str}")
            if len(available_items) > 20:
                print(f"   ... và {len(available_items) - 20} biến thể khác.")
            print("\n💡 Mẹo: Thêm cờ --probe để kiểm tra chính xác số lượng từng chiếc máy: python3 scripts/check_store_inventory.py <mã> --probe")

        # In hướng dẫn mở file HTML tương tác
        viewer_path = os.path.join(PROJECT_ROOT, "data/reports/fpt_store_inventory_viewer.html")
        apple_id_code = matched_shops[0].get("store_code") or target_shop_code
        print("\n" + "=" * 80)
        print(f"🌐 MỞ GIAO DIỆN WEB TRỰC QUAN:")
        print(f"   open \"{viewer_path}#store={apple_id_code}\"")
        print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tra cứu siêu thị FPT và kiểm tra tồn kho")
    parser.add_argument("query", type=str, help="Mã Shop (VD: 30878, 3815062) hoặc tên đường / địa chỉ")
    parser.add_argument("--sku", type=str, default=None, help="Mã SKU cụ thể cần kiểm tra")
    parser.add_argument("--probe", "-p", action="store_true", help="Dò chính xác số lượng chiếc thực tế của từng SKU tại quầy")
    args = parser.parse_args()

    check_store(args.query, args.sku, probe=args.probe)
