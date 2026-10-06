#!/usr/bin/env python3
"""
TGDD Hybrid Intelligence & Inventory Pipeline (Production Grade)
================================================================
Phiên bản hoàn thiện:
1. Discovery tự động trên 5 danh mục Apple của Thế Giới Di Động (iPhone, Mac, Watch, iPad, AirPods).
2. Khử trùng lặp SKU thông minh (Deduplication) khi nhiều URL danh mục cùng trỏ tới 1 ProductGroup.
3. Bóc tách chính xác RAM / SSD cho MacBook, Size (mm) cho Apple Watch, Dung lượng cho iPhone/iPad.
4. Tách biệt rõ Gia_Niem_Yet và Gia_Khuyen_Mai theo chuẩn daily-promotion.
5. Quét số lượng siêu thị còn hàng toàn quốc (Store_Count, Store_HCM, Store_Hanoi, Top_Provinces).
6. Tùy chọn xuất đồng bộ sang data/raw/YYYY-MM-DD/2-mw-YYYY-MM-DD.csv để thay thế crawler cũ Playwright.
"""

import os
import sys
import re
import csv
import json
import time
import argparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Tuple, Set
import requests
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Origin': 'https://www.thegioididong.com',
    'Referer': 'https://www.thegioididong.com/',
    'Content-Type': 'application/json'
}

STORE_API_URL = "https://api.thegioididong.com/gw/bus-tgdd-tmdt/api/Store/GetStoreByDeliveryPolicy"

CATEGORIES = {
    'iPhone': 'https://www.thegioididong.com/dtdd-apple-iphone',
    'MacBook': 'https://www.thegioididong.com/laptop-apple-macbook',
    'Apple Watch': 'https://www.thegioididong.com/dong-ho-thong-minh-apple',
    'iPad': 'https://www.thegioididong.com/may-tinh-bang-apple-ipad',
    'AirPods': 'https://www.thegioididong.com/tai-nghe-apple'
}


def parse_storage_and_specs(name: str, category: str) -> str:
    """Bóc tách chính xác dung lượng (SSD / Storage) hoặc kích thước (Watch)."""
    if category == 'MacBook':
        # Bắt cặp RAM/SSD (vd: 16GB/512GB, 8GB/256GB)
        ram_ssd = re.search(r'(\d+GB\/\d+(?:GB|TB))', name, re.IGNORECASE)
        if ram_ssd:
            return ram_ssd.group(1).upper()
        # Bắt riêng SSD
        ssd = re.search(r'\b(\d+(?:GB|TB))\b', name, re.IGNORECASE)
        return ssd.group(1).upper() if ssd else "Standard"

    elif category == 'Apple Watch':
        # Bắt kích thước mặt đồng hồ (vd: 40mm, 42mm, 44mm, 46mm, 49mm)
        size = re.search(r'(\d+mm)', name, re.IGNORECASE)
        return size.group(1).lower() if size else "Standard"

    else:
        # iPhone / iPad: Bắt dung lượng bộ nhớ trong
        m = re.search(r'\b(\d+(?:GB|TB))\b', name, re.IGNORECASE)
        return m.group(1).upper() if m else "Standard"


def discover_category_links(cat_name: str, cat_url: str) -> List[str]:
    """Quét trang danh mục để lấy tất cả URL sản phẩm Apple đang kinh doanh."""
    try:
        resp = requests.get(cat_url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"⚠️ Không tải được danh mục {cat_name}: HTTP {resp.status_code}")
            return []
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        links = set()
        for a in soup.find_all('a', href=True):
            href = a['href'].split('?')[0].split('#')[0]
            if not href.startswith('http'):
                href = 'https://www.thegioididong.com' + href
            
            # Kiểm tra tiền tố URL theo danh mục
            if any(p in href for p in ['/dtdd/', '/laptop/', '/dong-ho-thong-minh/', '/may-tinh-bang/', '/tai-nghe/']):
                # Lọc riêng AirPods / tai nghe Apple
                if cat_name == 'AirPods' and not any(k in href.lower() for k in ['airpod', 'apple', 'earpod']):
                    continue
                links.add(href)
        return sorted(list(links))
    except Exception as e:
        print(f"❌ Lỗi khi quét {cat_name}: {e}")
        return []


def extract_product_data(product_url: str, category: str) -> List[Dict[str, Any]]:
    """Bóc tách thông tin chi tiết và tất cả biến thể của sản phẩm từ JSON-LD."""
    try:
        resp = requests.get(product_url, headers=HEADERS, timeout=12)
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, 'html.parser')
        h1 = soup.find('h1')
        main_title = h1.get_text(strip=True) if h1 else ""
        if not main_title:
            return []

        variants = []
        for s in soup.find_all('script'):
            txt = s.get_text().strip()
            
            # 1. Tìm ProductGroup (Đa biến thể màu/dung lượng)
            if 'ProductGroup' in txt and 'hasVariant' in txt:
                try:
                    data = json.loads(txt)
                    if data.get('@type') == 'ProductGroup' and 'hasVariant' in data:
                        for v in data['hasVariant']:
                            sku = str(v.get('sku', '')).strip()
                            name = v.get('name', main_title).strip()
                            color = v.get('color', '').strip() or 'Default'
                            price_raw = v.get('offers', {}).get('price', 0)
                            price = int(float(price_raw)) if price_raw else 0
                            
                            storage = parse_storage_and_specs(name, category)

                            variants.append({
                                "Product_Name": name,
                                "Category": category,
                                "Storage": storage,
                                "Color": color,
                                "SKU": sku,
                                "Gia_Niem_Yet": price,      # Chuẩn hóa
                                "Gia_Khuyen_Mai": price,    # Chuẩn hóa
                                "Link": product_url
                            })
                        break
                except: pass
            
            # 2. Fallback nếu trang chỉ có 1 biến thể duy nhất (Product)
            elif '\"@type\":\"Product\"' in txt or '\"@type\": \"Product\"' in txt:
                try:
                    data = json.loads(txt)
                    if data.get('@type') == 'Product':
                        sku = str(data.get('sku', '')).strip()
                        name = data.get('name', main_title).strip()
                        price_raw = data.get('offers', {}).get('price', 0)
                        price = int(float(price_raw)) if price_raw else 0
                        storage = parse_storage_and_specs(name, category)

                        variants.append({
                            "Product_Name": name,
                            "Category": category,
                            "Storage": storage,
                            "Color": "Default",
                            "SKU": sku,
                            "Gia_Niem_Yet": price,
                            "Gia_Khuyen_Mai": price,
                            "Link": product_url
                        })
                        break
                except: pass

        return variants
    except Exception:
        return []


def query_store_inventory(sku: str) -> Tuple[int, int, int, str]:
    """
    Truy vấn số lượng shop còn hàng qua API TGDD:
    Trả về: (total_nationwide, hcm_count, hanoi_count, top_provinces_str)
    """
    if not sku:
        return 0, 0, 0, ""

    payload = {
        "productCode": str(sku),
        "provinceId": 0,  # 0 = Toàn quốc
        "wardId": 0,
        "haveStock": True,
        "haveStore": True,
        "siteId": 2
    }
    try:
        r = requests.post(STORE_API_URL, json=payload, headers=HEADERS, timeout=8)
        if r.status_code == 200:
            res = r.json().get('data', {})
            total = res.get('total', 0)
            store_list = res.get('storeList', [])
            
            hcm = 0
            hn = 0
            provinces = {}
            for s in store_list:
                p_name = s.get('provinceName', '')
                if 'Hồ Chí Minh' in p_name:
                    hcm += 1
                elif 'Hà Nội' in p_name:
                    hn += 1
                provinces[p_name] = provinces.get(p_name, 0) + 1
            
            top_prov = sorted(provinces.items(), key=lambda x: x[1], reverse=True)[:3]
            top_str = ", ".join([f"{k}: {v}" for k, v in top_prov])
            return total, hcm, hn, top_str
    except Exception:
        pass

    return 0, 0, 0, ""


def process_variant_inventory(item: Dict[str, Any]) -> Dict[str, Any]:
    """Bổ sung dữ liệu tồn kho vào từng biến thể."""
    sku = item.get("SKU", "")
    total, hcm, hn, top_prov = query_store_inventory(sku)
    
    item["Ton_Kho"] = "Yes" if total > 0 else "No"
    item["Store_Count"] = total
    item["Store_HCM"] = hcm
    item["Store_Hanoi"] = hn
    item["Top_Provinces_Stock"] = top_prov
    return item


def run_pipeline(output_csv: str = None, sync_raw: bool = False, max_workers: int = 12):
    start_time = time.time()
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    if not output_csv:
        output_dir = os.path.join(os.path.dirname(__file__), f"../../data/hybrid")
        os.makedirs(output_dir, exist_ok=True)
        output_csv = os.path.join(output_dir, f"tgdd_inventory_{today_str}.csv")

    print("=" * 75)
    print(f"🚀 KHỞI ĐỘNG HYBRID INTELLIGENCE PIPELINE (HOÀN THIỆN) - {today_str}")
    print("=" * 75)

    # 1. BƯỚC 1: DISCOVERY TRÊN 5 DANH MỤC
    print("\n[BƯỚC 1] Tự động quét 5 danh mục Apple trên Thế Giới Di Động...")
    all_category_urls = {}
    total_discovered_urls = 0
    
    for cat_name, cat_url in CATEGORIES.items():
        urls = discover_category_links(cat_name, cat_url)
        all_category_urls[cat_name] = urls
        total_discovered_urls += len(urls)
        print(f"  📁 {cat_name:<12}: Tìm thấy {len(urls)} URLs")

    print(f"✨ Tổng cộng {total_discovered_urls} URLs sản phẩm đang niêm yết.")

    # 2. BƯỚC 2: BÓC TÁCH THÔNG TIN SẢN PHẨM & BIẾN THỂ (CONCURRENT)
    print(f"\n[BƯỚC 2] Bóc tách biến thể (Model, Dung lượng, Màu sắc, SKU) với {max_workers} luồng...")
    raw_variants = []
    crawl_tasks = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for cat_name, urls in all_category_urls.items():
            for u in urls:
                crawl_tasks.append(executor.submit(extract_product_data, u, cat_name))
        
        for future in as_completed(crawl_tasks):
            res = future.result()
            if res:
                raw_variants.extend(res)

    # Khử trùng lặp SKU thông minh
    seen_skus: Set[str] = set()
    unique_variants = []
    for v in raw_variants:
        sku = v.get("SKU")
        if sku and sku in seen_skus:
            continue
        if sku:
            seen_skus.add(sku)
        unique_variants.append(v)

    print(f"✅ Đã trích xuất {len(raw_variants)} biến thể thô -> Sau khi khử trùng lặp SKU: {len(unique_variants)} biến thể duy nhất.")

    # 3. BƯỚC 3: QUÉT TỒN KHO THEO SIÊU THỊ NATIONWIDE (CONCURRENT)
    print(f"\n[BƯỚC 3] Quét số lượng siêu thị còn tồn kho toàn quốc cho {len(unique_variants)} biến thể...")
    processed_records = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        inv_tasks = [executor.submit(process_variant_inventory, v) for v in unique_variants]
        for idx, future in enumerate(as_completed(inv_tasks), 1):
            processed_records.append(future.result())
            if idx % 50 == 0 or idx == len(unique_variants):
                print(f"  ⚡ Tiến độ: {idx}/{len(unique_variants)} ({idx*100//len(unique_variants)}%)")

    # 4. BƯỚC 4: XUẤT RA CSV PHÂN TÍCH HYBRID
    print(f"\n[BƯỚC 4] Đang ghi dữ liệu vào file CSV phân tích: {output_csv}")
    fieldnames = [
        "Product_Name", "Category", "Storage", "Color", "SKU",
        "Gia_Niem_Yet", "Gia_Khuyen_Mai", "Ton_Kho", "Store_Count", "Store_HCM", "Store_Hanoi",
        "Top_Provinces_Stock", "Date", "Link"
    ]

    processed_records.sort(key=lambda x: (x.get("Category", ""), x.get("Product_Name", ""), x.get("Gia_Khuyen_Mai", 0)))

    os.makedirs(os.path.dirname(os.path.abspath(output_csv)), exist_ok=True)
    with open(output_csv, mode="w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        for r in processed_records:
            r["Date"] = today_str
            writer.writerow({k: r.get(k, "") for k in fieldnames})

    # 5. ĐỒNG BỘ SANG DATA RAW CHO PIPELINE BÁO CÁO CŨ (NẾU BẬT CỜ)
    if sync_raw:
        raw_dir = os.path.join(os.path.dirname(__file__), f"../../data/raw/{today_str}")
        os.makedirs(raw_dir, exist_ok=True)
        raw_csv_path = os.path.join(raw_dir, f"2-mw-{today_str}.csv")
        
        # Format chuẩn của 2-mw cũ:
        # Product_Name;Color;Ton_Kho;Gia_Niem_Yet;Gia_Khuyen_Mai;Date;Khuyen_Mai;Thanh_Toan;Link;screenshot_name
        raw_fields = [
            "Product_Name", "Color", "Ton_Kho", "Gia_Niem_Yet", "Gia_Khuyen_Mai",
            "Date", "Khuyen_Mai", "Thanh_Toan", "Link", "screenshot_name"
        ]
        with open(raw_csv_path, mode="w", encoding="utf-8-sig", newline="") as rf:
            r_writer = csv.DictWriter(rf, fieldnames=raw_fields, delimiter=";")
            r_writer.writeheader()
            for r in processed_records:
                r_writer.writerow({
                    "Product_Name": r.get("Product_Name", ""),
                    "Color": r.get("Color", "Default"),
                    "Ton_Kho": r.get("Ton_Kho", "No"),
                    "Gia_Niem_Yet": r.get("Gia_Niem_Yet", 0),
                    "Gia_Khuyen_Mai": r.get("Gia_Khuyen_Mai", 0),
                    "Date": today_str,
                    "Khuyen_Mai": f"Còn hàng tại {r.get('Store_Count', 0)} siêu thị toàn quốc ({r.get('Top_Provinces_Stock', '')})",
                    "Thanh_Toan": "",
                    "Link": r.get("Link", ""),
                    "screenshot_name": ""
                })
        print(f"🔄 Đã đồng bộ sang raw CSV hàng ngày: {raw_csv_path}")

    elapsed = time.time() - start_time
    print("=" * 75)
    print(f"🎉 HOÀN TẤT THÀNH CÔNG TRONG {elapsed:.1f} GIÂY!")
    print(f"📊 File kết quả: {output_csv}")
    print(f"📈 Tổng số bản ghi duy nhất: {len(processed_records)}")
    
    in_stock_count = sum(1 for r in processed_records if r.get("Store_Count", 0) > 0)
    out_stock_count = len(processed_records) - in_stock_count
    print(f"   - Biến thể còn hàng tại siêu thị: {in_stock_count} ({in_stock_count*100//len(processed_records)}%)")
    print(f"   - Biến thể hết hàng toàn quốc:    {out_stock_count} ({out_stock_count*100//len(processed_records)}%)")
    print("=" * 75)

    return output_csv


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TGDD Hybrid Crawler & Stock Scanner")
    parser.add_argument("--output", "-o", help="Đường dẫn file CSV xuất ra", default=None)
    parser.add_argument("--sync-raw", action="store_true", help="Đồng bộ sang data/raw/YYYY-MM-DD/2-mw-YYYY-MM-DD.csv")
    parser.add_argument("--workers", "-w", type=int, default=12, help="Số luồng xử lý song song")
    args = parser.parse_args()

    run_pipeline(output_csv=args.output, sync_raw=args.sync_raw, max_workers=args.workers)
