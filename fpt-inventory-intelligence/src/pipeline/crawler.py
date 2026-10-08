"""
FPT High-Speed Hybrid API Crawler & Deep Inventory Scanner
===========================================================
Tích hợp:
1. Category & Slug Discovery (Ecosystem Apple: iPhone, Mac, iPad, Watch, AirPods).
2. Product Variants & Central Inventory Extraction (Lấy mã SKU, giá, tồn kho tổng).
3. Trade-In Subsidy Extraction (Chính sách trợ giá thu cũ đổi mới).
4. Store-Level Real-Time Inventory (Quét 34 tỉnh bằng Smart Fulfillment API trong < 1.5s).
5. Phân loại kép: Hệ thống FPT Shop (channel 1) & Hệ thống cao cấp Apple F.Studio by FPT (channel 12).
6. Làm giàu dữ liệu GPS từ FPTStoreMasterRegistry.
"""

import os
import sys
import re
import csv
import json
import time
import shutil
import argparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Set, Tuple, Optional

import requests
from bs4 import BeautifulSoup

# Thêm PROJECT_ROOT vào sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import (
    RAW_DATA_DIR,
    VARIANT_API_URL,
    TRADE_IN_API_URL,
    PICKUP_API_URL,
    HEADERS_FPTSHOP,
    HEADERS_FSTUDIO,
    ACTIVE_PROVINCES,
    KEY_PROVINCES,
    CATEGORY_URLS,
    SLUGS_CACHE_FILE
)
from src.pipeline.store_master import FPTStoreMasterRegistry


def discover_category_slugs(cat_name: str, cat_url: str) -> List[str]:
    """Quét trang danh mục để tìm toàn bộ slug sản phẩm Apple đang kinh doanh (có cache fallback)."""
    slugs = set()
    try:
        resp = requests.get(cat_url, headers=HEADERS_FPTSHOP, timeout=8)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"].split("?")[0].strip()
                # Bắt các link sản phẩm đặc thù theo danh mục
                if any(href.startswith(prefix) for prefix in [
                    "/dien-thoai/iphone-",
                    "/may-tinh-xach-tay/macbook-",
                    "/may-tinh-bang/ipad-",
                    "/smartwatch/apple-watch-",
                    "/phu-kien/tai-nghe-airpods-"
                ]):
                    clean_slug = href.lstrip("/")
                    slugs.add(clean_slug)
    except Exception:
        pass

    # Nếu HTML bị chặn hoặc không bắt được link, dùng cache master slugs
    if not slugs and os.path.exists(SLUGS_CACHE_FILE):
        try:
            with open(SLUGS_CACHE_FILE, "r", encoding="utf-8") as f:
                cache = json.load(f)
                cached_list = cache.get(cat_name, [])
                if cached_list:
                    return cached_list
        except Exception:
            pass

    return sorted(slugs)


def fetch_product_variants(slug: str) -> Optional[Dict[str, Any]]:
    """Gọi API bóc tách toàn bộ biến thể SKU, màu sắc, giá và tồn kho tổng."""
    try:
        resp = requests.get(VARIANT_API_URL, headers=HEADERS_FPTSHOP, params={"slug": slug}, timeout=8)
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            if data and data.get("skus"):
                return data
    except Exception as e:
        print(f"⚠️ Lỗi gọi API biến thể slug {slug}: {e}")
    return None


def fetch_trade_in_subsidies(slug: str) -> Dict[str, Any]:
    """Lấy thông tin trợ giá thu cũ đổi mới từ FPT Shop."""
    try:
        resp = requests.get(TRADE_IN_API_URL, headers=HEADERS_FPTSHOP, params={"slug": slug}, timeout=5)
        if resp.status_code == 200:
            return resp.json().get("data", {})
    except Exception:
        pass
    return {}


def scan_store_inventory_for_sku(
    sku_code: str,
    sku_name: str,
    price: int,
    order_channel: str = "1",
    max_workers: int = 17
) -> List[Dict[str, Any]]:
    """
    Quét tồn kho thực tế tại từng siêu thị trên toàn quốc cho một SKU cụ thể.
    order_channel: "1" cho FPT Shop, "12" cho F.Studio.
    """
    headers = HEADERS_FPTSHOP if order_channel == "1" else HEADERS_FSTUDIO
    all_stores = []

    def query_province(p_code: str):
        payload = {
            "cityCode": p_code,
            "orderDoctotal": price if price > 0 else 10000000,
            "product": [{
                "id": sku_code,
                "name": sku_name,
                "quantity": 1,
                "price": price if price > 0 else 10000000,
                "unit": 8,
                "isCheckInventory": True
            }]
        }
        try:
            r = requests.post(PICKUP_API_URL, headers=headers, json=payload, timeout=6)
            if r.status_code == 200:
                return r.json().get("data", [])
        except Exception:
            pass
        return []

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(query_province, c) for c in ACTIVE_PROVINCES]
        for f in as_completed(futures):
            stores = f.result()
            if stores:
                all_stores.extend(stores)

    return all_stores


def run_pipeline(
    output_csv: Optional[str] = None,
    output_json: Optional[str] = None,
    max_workers: int = 12,
    mode: str = "deep",
    target_category: Optional[str] = None
) -> Tuple[str, str]:
    """
    Thực thi chu trình cào tồn kho FPT Shop & F.Studio.
    mode: 'fast' (quét nhanh kho tổng 3-5s) hoặc 'deep' (quét sâu 602 siêu thị).
    target_category: 'iPhone', 'iPad', 'MacBook', 'Apple Watch', 'AirPods' hoặc None (tất cả).
    """
    start_time = time.time()
    now = datetime.now()
    timestamp_str = now.strftime("%Y-%m-%d_%H%M")
    today_str = now.strftime("%Y-%m-%d")

    print("=" * 80)
    print(f"🚀 BẮT ĐẦU FPT INVENTORY PIPELINE (Chế độ: {mode.upper()})")
    print(f"Thời gian: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # 1. Nạp Master Store Registry
    registry = FPTStoreMasterRegistry()

    # 2. Khám phá slugs theo danh mục Apple
    print("\n🔍 BƯỚC 1: Khám phá sản phẩm Apple trên FPT Shop...")
    categories_to_scan = CATEGORY_URLS
    if target_category and target_category in CATEGORY_URLS:
        categories_to_scan = {target_category: CATEGORY_URLS[target_category]}

    all_slugs_by_cat = {}
    for cat_name, cat_url in categories_to_scan.items():
        slugs = discover_category_slugs(cat_name, cat_url)
        all_slugs_by_cat[cat_name] = slugs
        print(f"  • {cat_name:<15}: {len(slugs):2d} sản phẩm")

    total_slugs = sum(len(s) for s in all_slugs_by_cat.values())
    print(f"👉 Tổng cộng: {total_slugs} sản phẩm Apple phát hiện.")

    # 3. Thu thập biến thể SKU & Tồn kho tổng
    print("\n📦 BƯỚC 2: Bóc tách biến thể SKU, giá & số lượng tồn kho tổng...")
    sku_tasks = []
    for cat_name, slugs in all_slugs_by_cat.items():
        for slug in slugs:
            sku_tasks.append((cat_name, slug))

    slug_variants = {}
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(fetch_product_variants, slug): (cat, slug) for cat, slug in sku_tasks}
        for f in as_completed(futures):
            cat, slug = futures[f]
            res = f.result()
            if res:
                slug_variants[slug] = (cat, res)

    print(f"✅ Đã nạp thành công biến thể cho {len(slug_variants)}/{total_slugs} dòng sản phẩm.")

    # 4. Quét tồn kho tại từng siêu thị cho các SKU đang kinh doanh
    print("\n🏬 BƯỚC 3: Quét tồn kho thực tế 602 siêu thị trên toàn quốc (FPT Shop & F.Studio)...")
    deep_inventory_records = []
    flat_records = []

    # Thu thập tất cả các biến thể SKU
    all_skus_to_scan = []
    for slug, (cat, p_data) in slug_variants.items():
        prod_name = p_data.get("name", "")
        for s in p_data.get("skus", []):
            all_skus_to_scan.append({
                "category": cat,
                "slug": slug,
                "product_name": prod_name,
                "sku_code": s.get("code"),
                "sku_name": s.get("name"),
                "display_name": s.get("displayName"),
                "price": s.get("price", 0),
                "total_inventory": s.get("inventory", 0),
                "type": s.get("type", "Normal")
            })

    print(f"📈 Tổng số biến thể SKU cần rà soát: {len(all_skus_to_scan)}")

    # Quét tồn kho tại siêu thị
    for idx, item in enumerate(all_skus_to_scan, 1):
        sku_code = item["sku_code"]
        sku_name = item["sku_name"]
        price = item["price"]
        tot_inv = item["total_inventory"]

        # Nếu ở chế độ 'fast' hoặc kho tổng = 0: bỏ qua quét 34 tỉnh để đạt tốc độ cao nhất (3-5s)
        if mode == "fast" or tot_inv == 0:
            in_stock_fpt = []
            in_stock_fstudio = []
        else:
            raw_fpt = scan_store_inventory_for_sku(sku_code, sku_name, price, order_channel="1")
            raw_fstudio = scan_store_inventory_for_sku(sku_code, sku_name, price, order_channel="12")
            # Lọc chính xác các siêu thị CÓ HÀNG SẴN LẤY NGAY (pickupType == 0)
            in_stock_fpt = [s for s in raw_fpt if s.get("pickupType") == 0]
            in_stock_fstudio = [s for s in raw_fstudio if s.get("pickupType") == 0]

        # Làm giàu thông tin siêu thị từ Registry
        enriched_fpt_stores = []
        for s in in_stock_fpt:
            sc = s.get("shopCode")
            master_s = registry.get_by_code(sc)
            enriched_fpt_stores.append({
                "shopCode": sc,
                "shopName": s.get("shopName"),
                "store_code": master_s.get("store_code") if master_s else None,
                "store_name": master_s.get("store_name") if master_s else None,
                "cluster_group": master_s.get("cluster_group") if master_s else None,
                "asm_group": master_s.get("asm_group") if master_s else None,
                "address": s.get("displayAddress"),
                "legacyAddress": s.get("oldDisplayAddress") or (master_s.get("legacyAddress") if master_s else ""),
                "provinceCode": s.get("cityCode"),
                "provinceName": s.get("cityName"),
                "channel": "FPT Shop",
                "latitude": s.get("location", {}).get("latitude"),
                "longitude": s.get("location", {}).get("longitude"),
                "timeOpen": s.get("timeOpen"),
                "timeClose": s.get("timeClose")
            })

        enriched_fstudio_stores = []
        for s in in_stock_fstudio:
            sc = s.get("shopCode")
            master_s = registry.get_by_code(sc)
            enriched_fstudio_stores.append({
                "shopCode": sc,
                "shopName": s.get("shopName"),
                "store_code": master_s.get("store_code") if master_s else None,
                "store_name": master_s.get("store_name") if master_s else None,
                "cluster_group": master_s.get("cluster_group") if master_s else None,
                "asm_group": master_s.get("asm_group") if master_s else None,
                "address": s.get("displayAddress"),
                "legacyAddress": s.get("oldDisplayAddress") or (master_s.get("legacyAddress") if master_s else ""),
                "provinceCode": s.get("cityCode"),
                "provinceName": s.get("cityName"),
                "channel": "F.Studio by FPT",
                "latitude": s.get("location", {}).get("latitude"),
                "longitude": s.get("location", {}).get("longitude"),
                "timeOpen": s.get("timeOpen"),
                "timeClose": s.get("timeClose")
            })

        hcm_count = sum(1 for s in enriched_fpt_stores if s.get("provinceCode") == "79")
        hn_count = sum(1 for s in enriched_fpt_stores if s.get("provinceCode") == "01")
        fstudio_count = len(enriched_fstudio_stores)

        deep_record = {
            "sku_code": sku_code,
            "sku_name": sku_name,
            "product_name": item["product_name"],
            "category": item["category"],
            "slug": item["slug"],
            "url": f"https://fptshop.com.vn/{item['slug']}?sku={sku_code}",
            "price": price,
            "total_inventory_quantity": tot_inv,
            "total_fpt_stores": len(enriched_fpt_stores),
            "total_fstudio_stores": fstudio_count,
            "hcm_stores": hcm_count,
            "hn_stores": hn_count,
            "fpt_store_list": enriched_fpt_stores,
            "fstudio_store_list": enriched_fstudio_stores
        }
        deep_inventory_records.append(deep_record)

        # Bóc tách màu sắc từ tên
        color_match = re.search(r'\b(Hồng|Xanh dương|Đen|Trắng|Bạc|Titan[^\s]+|Vàng|Xám|Tím)\b', sku_name, re.IGNORECASE)
        color = color_match.group(1).capitalize() if color_match else "Default"

        flat_record = {
            "Product_Name": item["product_name"],
            "SKU": sku_code,
            "Color": color,
            "Ton_Kho": "Yes" if len(enriched_fpt_stores) > 0 or tot_inv > 0 else "No",
            "Total_Inventory_Qty": tot_inv,
            "FPT_Store_Count": len(enriched_fpt_stores),
            "FStudio_Store_Count": fstudio_count,
            "HCM_Stores": hcm_count,
            "HN_Stores": hn_count,
            "Gia_Khuyen_Mai": price,
            "Category": item["category"],
            "Date": today_str,
            "Link": deep_record["url"]
        }
        flat_records.append(flat_record)

        if idx % 10 == 0 or idx == len(all_skus_to_scan):
            print(f"  [{idx:3d}/{len(all_skus_to_scan)}] {item['sku_name'][:40]:<40} | Tồn tổng: {tot_inv:3d} | FPT: {len(enriched_fpt_stores):3d} shop | F.Studio: {fstudio_count:2d} shop")

    # 5. Lưu trữ kết quả
    if not output_json:
        output_json = os.path.join(RAW_DATA_DIR, f"fpt_inventory_deep_{timestamp_str}.json")
    if not output_csv:
        output_csv = os.path.join(RAW_DATA_DIR, f"fpt_inventory_{timestamp_str}.csv")

    latest_json = os.path.join(RAW_DATA_DIR, "fpt_inventory_deep_latest.json")
    latest_csv = os.path.join(RAW_DATA_DIR, "fpt_inventory_latest.csv")

    if flat_records:
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(deep_inventory_records, f, ensure_ascii=False, indent=2)
        shutil.copyfile(output_json, latest_json)

        keys = list(flat_records[0].keys())
        with open(output_csv, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys, delimiter=";")
            writer.writeheader()
            writer.writerows(flat_records)
        shutil.copyfile(output_csv, latest_csv)

    elapsed = time.time() - start_time
    print("\n" + "=" * 80)
    print(f"🎉 HOÀN TẤT THÀNH CÔNG TRONG {elapsed:.1f} GIÂY!")
    if flat_records:
        print(f"📊 1. Snapshot JSON sâu: {output_json}")
        print(f"📊 2. Snapshot CSV phẳng: {output_csv}")
        print(f"📈 Tổng biến thể xử lý: {len(flat_records)}")
        in_stock_skus = sum(1 for r in flat_records if r["Ton_Kho"] == "Yes")
        pct = in_stock_skus * 100 // len(flat_records) if len(flat_records) > 0 else 0
        print(f"   • Biến thể có hàng:  {in_stock_skus} ({pct}%)")
        print(f"   • Biến thể cạn hàng: {len(flat_records) - in_stock_skus}")
    else:
        print("⚠️ Không có biến thể nào được thu thập (vui lòng kiểm tra kết nối mạng).")
    print("=" * 80)

    return output_csv, output_json


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FPT High-Speed Hybrid Inventory Crawler")
    parser.add_argument("--workers", "-w", type=int, default=12, help="Số luồng xử lý")
    parser.add_argument("--mode", "-m", choices=["fast", "deep"], default="deep", help="Chế độ quét: 'fast' (quét nhanh kho tổng 3-5s) hoặc 'deep' (quét sâu 602 siêu thị)")
    parser.add_argument("--category", "-c", type=str, default=None, help="Chỉ quét 1 ngành hàng cụ thể (iPhone, iPad, MacBook, Apple Watch, AirPods)")
    args = parser.parse_args()
    run_pipeline(max_workers=args.workers, mode=args.mode, target_category=args.category)
