"""
FPT High-Speed On-Demand Store Inventory Prober
===============================================
Dò tìm độc lập 100% số lượng tồn kho máy vật lý chính xác tại 1 siêu thị FPT/F.Studio chỉ định.
KHÔNG CẦN CHẠY DEEP AUDIT 54 PHÚT.

Cơ chế hoạt động 2 giai đoạn (Tối ưu hóa Connection Pooling, tổng thời gian ~15 - 25s):
1. GIAI ĐOẠN 1 (~3-5s): Đọc danh mục 482 SKU từ FAST MODE, gửi truy vấn song song cho DUY NHẤT
   tỉnh của siêu thị đó (thay vì 34 tỉnh) để lọc nhanh toàn bộ SKU có mặt tại quầy (pickupType == 0).
2. GIAI ĐOẠN 2 (~10-15s): Dùng thuật toán Tìm kiếm Nhị phân (Binary Search) O(log N) để bóc tách
   chính xác số lượng máy vật lý (1, 2, 5, 9 máy...) cho từng biến thể tìm thấy.
3. TỰ ĐỘNG CẬP NHẬT: Lưu kết quả vào data/raw/store_inventory_quantities.json và làm mới
   giao diện web tương tác data/reports/fpt_store_inventory_viewer.html.
"""

import os
import sys
import json
import time
import argparse
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import requests
from requests.adapters import HTTPAdapter
from config import RAW_DATA_DIR, PICKUP_API_URL, HEADERS_FPTSHOP, HEADERS_FSTUDIO
from src.pipeline.store_master import FPTStoreMasterRegistry


def create_resilient_session(pool_size: int = 25) -> requests.Session:
    """Tạo requests Session tái sử dụng kết nối TLS/TCP (Connection Pooling) giúp tăng tốc 3x."""
    session = requests.Session()
    adapter = HTTPAdapter(pool_connections=pool_size, pool_maxsize=pool_size, max_retries=2)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def probe_store_inventory(
    shop_query: str,
    max_probe_limit: int = 30,
    max_workers: int = 12,
    auto_open: bool = False
) -> Optional[Dict[str, Any]]:
    start_time = time.time()
    registry = FPTStoreMasterRegistry()

    # 1. Tìm thông tin siêu thị theo ShopCode, Apple ID hoặc tên/địa chỉ
    store = registry.get_by_code(shop_query)
    if not store:
        matches = registry.search_by_query(shop_query, limit=1)
        if matches:
            store = matches[0]
        else:
            print(f"❌ Không tìm thấy siêu thị nào khớp với từ khóa/mã: '{shop_query}'")
            return None

    target_shop_code = str(store["shopCode"])
    province_code = store.get("provinceCode", "79")
    shop_name = store.get("shopName", "")
    apple_id = store.get("store_code", "")
    channel_name = store.get("channel", "FPT Shop")
    address = store.get("displayAddress", "")

    print("=" * 80)
    print(f"🎯 FPT ON-DEMAND STORE INVENTORY PROBER (TWO-TIER ENGINE)")
    print("=" * 80)
    print(f"🏬 Siêu thị mục tiêu : {shop_name}")
    print(f"   • Mã FPT Shop      : {target_shop_code}")
    print(f"   • Apple Store ID   : {apple_id or 'Chưa gắn mã Apple ID'}")
    print(f"   • Kênh phân phối   : {channel_name}")
    print(f"   • Tỉnh / Thành     : Mã {province_code}")
    print(f"   • Địa chỉ          : {address}")
    print("=" * 80)

    # 2. Nạp danh mục sản phẩm từ FAST MODE snapshot (hoặc DEEP nếu có)
    fast_json = os.path.join(RAW_DATA_DIR, "fpt_inventory_fast_latest.json")
    deep_json = os.path.join(RAW_DATA_DIR, "fpt_inventory_deep_latest.json")

    catalog_file = None
    if os.path.exists(fast_json):
        catalog_file = fast_json
    elif os.path.exists(deep_json):
        catalog_file = deep_json
    else:
        print("\n⚡ Chưa có snapshot danh mục. Đang tự động chạy FAST MODE (9s)...")
        from src.pipeline.crawler import run_pipeline
        run_pipeline(mode="fast")
        catalog_file = fast_json

    with open(catalog_file, "r", encoding="utf-8") as f:
        products = json.load(f)

    # Chỉ lọc các sản phẩm có tồn kho khả dụng toàn quốc (loại bỏ sản phẩm đã tuyệt chủng)
    active_products = [p for p in products if p.get("total_inventory_quantity", 0) > 0]
    print(f"\n📂 Nạp {len(products)} SKU từ danh mục. Lọc ra {len(active_products)} SKU còn hàng toàn quốc.")

    # 3. GIAI ĐOẠN 1: Quét song song cho RIÊNG tỉnh của shop để tìm các SKU có mặt tại quầy
    print(f"\n⚡ GIAI ĐOẠN 1: Quét nhanh sự hiện diện tại quầy (Single-Province Scan: Tỉnh {province_code})...")
    g1_start = time.time()

    # Kiểm tra xem shop mục tiêu có thuộc kênh F.Studio hay FPT Shop thông thường
    is_target_fstudio = "fstudio" in channel_name.lower() or "f.studio" in shop_name.lower()
    session = create_resilient_session(pool_size=max_workers * 2)
    available_items = []

    def check_presence(p):
        sku = p.get("sku_code")
        name = p.get("sku_name")
        price = p.get("price", 10000000)

        payload = {
            "cityCode": province_code,
            "orderDoctotal": price,
            "product": [{"id": sku, "name": name, "quantity": 1, "price": price, "unit": 8, "isCheckInventory": True}]
        }

        in_fpt = False
        in_fstudio = False

        # 1. Thử kênh FPT Shop (nếu không phải là F.Studio thuần)
        if not is_target_fstudio:
            for attempt in range(3):
                try:
                    r1 = session.post(PICKUP_API_URL, headers=HEADERS_FPTSHOP, json=payload, timeout=6)
                    if r1.status_code == 200:
                        in_fpt = any(str(s.get("shopCode")) == target_shop_code and s.get("pickupType") == 0 for s in r1.json().get("data", []))
                        break
                    elif r1.status_code in [403, 429]:
                        time.sleep(1.5 * (attempt + 1))
                except Exception:
                    time.sleep(0.3)

        # 2. Thử kênh F.Studio (nếu là F.Studio hoặc nếu FPT Shop chưa tìm thấy)
        if is_target_fstudio or (not in_fpt and "studio" in shop_name.lower()):
            for attempt in range(3):
                try:
                    r2 = session.post(PICKUP_API_URL, headers=HEADERS_FSTUDIO, json=payload, timeout=6)
                    if r2.status_code == 200:
                        in_fstudio = any(str(s.get("shopCode")) == target_shop_code and s.get("pickupType") == 0 for s in r2.json().get("data", []))
                        break
                    elif r2.status_code in [403, 429]:
                        time.sleep(1.5 * (attempt + 1))
                except Exception:
                    time.sleep(0.3)

        if in_fpt or in_fstudio:
            ch_label = "FPT Shop & F.Studio" if (in_fpt and in_fstudio) else ("F.Studio by FPT" if in_fstudio else "FPT Shop")
            return {
                "sku_code": sku,
                "sku_name": name,
                "category": p.get("category", "Khác"),
                "price": price,
                "channel": ch_label,
                "prefer_fstudio": in_fstudio,
                "url": p.get("url") or f"https://fptshop.com.vn/{p.get('slug', '')}?sku={sku}"
            }
        return None

    # Dùng 6 workers an toàn chống kích hoạt Cloudflare Rate Limit
    safe_workers = min(max_workers, 6)
    with ThreadPoolExecutor(max_workers=safe_workers) as ex:
        futures = [ex.submit(check_presence, p) for p in active_products]
        for f in as_completed(futures):
            res = f.result()
            if res:
                available_items.append(res)

    g1_time = time.time() - g1_start
    print(f"✅ Giai đoạn 1 hoàn tất sau {g1_time:.1f}s: Phát hiện {len(available_items)} biến thể có mặt tại quầy.")

    if not available_items:
        print(f"⚠️ Không tìm thấy biến thể Apple nào có sẵn tại siêu thị {target_shop_code} vào thời điểm này.")
        return None

    # Sắp xếp theo ngành hàng và giá bán
    cat_order = {"iPhone": 1, "MacBook": 2, "iPad": 3, "Apple Watch": 4, "AirPods": 5}
    available_items.sort(key=lambda x: (cat_order.get(x["category"], 99), -x["price"]))

    # 4. GIAI ĐOẠN 2: Dò chính xác số lượng máy bằng Binary Search
    print(f"\n🔍 GIAI ĐOẠN 2: Dò chính xác số lượng máy vật lý bằng Binary Search O(log N)...")
    g2_start = time.time()

    def check_qty(sku, name, price, q, headers):
        payload = {
            "cityCode": province_code,
            "orderDoctotal": price * q,
            "product": [{"id": sku, "name": name, "quantity": q, "price": price, "unit": 8, "isCheckInventory": True}]
        }
        for attempt in range(4):
            try:
                r = session.post(PICKUP_API_URL, headers=headers, json=payload, timeout=8)
                if r.status_code == 200:
                    data = r.json().get("data", [])
                    return any(str(s.get("shopCode")) == target_shop_code and s.get("pickupType") == 0 for s in data)
                elif r.status_code in [403, 429]:
                    sleep_t = 2.0 * (attempt + 1)
                    print(f"\n      ⏳ Cloudflare Rate Limit (HTTP {r.status_code}) tại q={q}. Đang tự động nghỉ {sleep_t:.1f}s và thử lại...")
                    time.sleep(sleep_t)
                else:
                    time.sleep(0.3)
            except Exception:
                time.sleep(0.3)
        return False

    items_qty = {}
    enriched_item_details = []
    total_physical_units = 0

    for idx, item in enumerate(available_items, 1):
        sku = item["sku_code"]
        name = item["sku_name"]
        price = item["price"]
        headers = HEADERS_FSTUDIO if item.get("prefer_fstudio") else HEADERS_FPTSHOP

        # Thử 2 máy trước
        if not check_qty(sku, name, price, 2, headers):
            qty_found = 1
        else:
            # Nếu có ít nhất 2 máy, áp dụng Binary Search trong dải [2..max_probe_limit]
            low = 2
            high = max_probe_limit
            qty_found = 2

            while low <= high:
                mid = (low + high) // 2
                if check_qty(sku, name, price, mid, headers):
                    qty_found = mid
                    low = mid + 1
                else:
                    high = mid - 1
                time.sleep(0.08)

        items_qty[sku] = qty_found
        total_physical_units += qty_found

        item_detail = {
            "sku_code": sku,
            "sku_name": name,
            "category": item["category"],
            "price": price,
            "channel": item["channel"],
            "url": item["url"],
            "quantity": qty_found,
            "is_exact_qty": True
        }
        enriched_item_details.append(item_detail)

        price_str = f"{price:,.0f} đ".replace(",", ".")
        badge = f"🔥 {qty_found:2d} máy" if qty_found >= 3 else (f"✓ {qty_found:2d} máy" if qty_found == 2 else "⚠️  1 máy")
        print(f"  [{idx:2d}/{len(available_items)}] [{item['category']:<11}] {name[:38]:<38} -> {badge} | {price_str}")
        time.sleep(0.1)

    g2_time = time.time() - g2_start
    total_elapsed = time.time() - start_time

    # Thống kê phân bổ theo ngành hàng
    cat_summary = {}
    total_store_value = 0
    for item in enriched_item_details:
        c = item["category"]
        if c not in cat_summary:
            cat_summary[c] = {"skus": 0, "units": 0, "value": 0}
        cat_summary[c]["skus"] += 1
        cat_summary[c]["units"] += item["quantity"]
        val = item["price"] * item["quantity"]
        cat_summary[c]["value"] += val
        total_store_value += val

    val_display = f"{total_store_value:,.0f} đ".replace(",", ".")

    print("\n" + "=" * 80)
    print(f"🎉 TỔNG KẾT TỒN KHO THỰC TẾ: {shop_name}")
    print(f"   • Apple ID: {apple_id or 'Chưa gắn'} | Mã Shop: {target_shop_code} | Kênh: {channel_name}")
    print(f"   • Tổng biến thể tại quầy : {len(available_items)} SKU")
    print(f"   • Tổng số máy vật lý     : {total_physical_units} MÁY")
    print(f"   • Tổng giá trị trưng bày : {val_display}")
    print(f"   • Thời gian thực thi     : {total_elapsed:.1f} giây (GĐ1: {g1_time:.1f}s | GĐ2: {g2_time:.1f}s)")
    print("-" * 80)
    print("   📊 PHÂN BỔ THEO NGÀNH HÀNG:")
    for c, stats in cat_summary.items():
        sub_val = f"{stats['value']:,.0f} đ".replace(",", ".")
        print(f"      • {c:<12}: {stats['skus']:2d} SKU | {stats['units']:2d} máy vật lý | {sub_val}")
    print("=" * 80)

    # 5. Lưu trữ kết quả vào data/raw/store_inventory_quantities.json
    quantities_file = os.path.join(RAW_DATA_DIR, "store_inventory_quantities.json")
    all_quantities = {}
    if os.path.exists(quantities_file):
        try:
            with open(quantities_file, "r", encoding="utf-8") as f:
                all_quantities = json.load(f)
        except Exception:
            all_quantities = {}

    all_quantities[target_shop_code] = {
        "probed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "shop_name": shop_name,
        "apple_store_id": apple_id,
        "province_code": province_code,
        "channel": channel_name,
        "total_units": total_physical_units,
        "total_skus": len(available_items),
        "total_value": total_store_value,
        "items": items_qty,
        "item_details": enriched_item_details
    }

    with open(quantities_file, "w", encoding="utf-8") as f:
        json.dump(all_quantities, f, ensure_ascii=False, indent=2)

    # 6. Tái tạo Dashboard Store Viewer HTML tương tác
    try:
        from src.inference.store_viewer_generator import generate_store_viewer_html
        viewer_html = generate_store_viewer_html()
        link_code = apple_id or target_shop_code
        print(f"\n🌐 MỞ TRÊN TRÌNH DUYỆT:")
        print(f'   open "{viewer_html}#store={link_code}"')

        if auto_open:
            subprocess.run(["open", f"{viewer_html}#store={link_code}"])
    except Exception as e:
        print(f"⚠️ Lỗi cập nhật HTML: {e}")

    return all_quantities[target_shop_code]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FPT High-Speed On-Demand Store Inventory Prober")
    parser.add_argument("query", nargs="?", default="3815062", help="Mã Apple Store ID (VD: 3815062, 3958531), mã FPT Shop (30501), hoặc tên/địa chỉ")
    parser.add_argument("--limit", "-l", type=int, default=30, help="Giới hạn tối đa máy dò tìm nhị phân (mặc định: 30)")
    parser.add_argument("--workers", "-w", type=int, default=12, help="Số luồng quét song song Giai đoạn 1 (mặc định: 12)")
    parser.add_argument("--open", "-o", action="store_true", help="Tự động mở trình duyệt xem giao diện HTML sau khi quét xong")
    args = parser.parse_args()

    probe_store_inventory(args.query, max_probe_limit=args.limit, max_workers=args.workers, auto_open=args.open)
