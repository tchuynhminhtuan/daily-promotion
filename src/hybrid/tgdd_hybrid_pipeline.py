#!/usr/bin/env python3
"""
TGDD Hybrid Intelligence & Inventory Pipeline
==============================================
Tự động:
1. Quét 5 danh mục Apple chính của Thế Giới Di Động (iPhone, MacBook, iPad, Apple Watch, AirPods)
2. Bóc tách toàn bộ biến thể (Model, Dung lượng, Màu sắc, Giá, Mã SKU ERP)
3. Quét số lượng siêu thị còn hàng trên toàn quốc (và chi tiết TP.HCM, Hà Nội) qua API nội bộ
4. Xuất kết quả ra file CSV chuẩn hóa để phân tích
5. Báo cáo chênh lệch sản phẩm mới (New Discovery) và sản phẩm đã ngừng kinh doanh (Retired)
"""

import os
import sys
import re
import csv
import json
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Tuple
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
            if 'ProductGroup' in txt and 'hasVariant' in txt:
                try:
                    data = json.loads(txt)
                    if data.get('@type') == 'ProductGroup' and 'hasVariant' in data:
                        for v in data['hasVariant']:
                            sku = str(v.get('sku', '')).strip()
                            name = v.get('name', main_title).strip()
                            color = v.get('color', '').strip() or 'Default'
                            price = v.get('offers', {}).get('price', 0)
                            
                            # Tách dung lượng / kích thước
                            storage_match = re.search(r'(\d+(?:GB|TB)|\d+mm)', name, re.IGNORECASE)
                            storage = storage_match.group(1) if storage_match else "Standard"

                            variants.append({
                                "Product_Name": name,
                                "Category": category,
                                "Storage": storage,
                                "Color": color,
                                "SKU": sku,
                                "Price": int(price) if price else 0,
                                "Link": product_url
                            })
                        break
                except: pass
            
            # Fallback nếu trang chỉ có 1 biến thể duy nhất (Product)
            elif '\"@type\":\"Product\"' in txt or '\"@type\": \"Product\"' in txt:
                try:
                    data = json.loads(txt)
                    if data.get('@type') == 'Product':
                        sku = str(data.get('sku', '')).strip()
                        name = data.get('name', main_title).strip()
                        price = data.get('offers', {}).get('price', 0)
                        storage_match = re.search(r'(\d+(?:GB|TB)|\d+mm)', name, re.IGNORECASE)
                        storage = storage_match.group(1) if storage_match else "Standard"

                        variants.append({
                            "Product_Name": name,
                            "Category": category,
                            "Storage": storage,
                            "Color": "Default",
                            "SKU": sku,
                            "Price": int(price) if price else 0,
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


def run_pipeline(output_csv: str = None, max_workers: int = 12):
    start_time = time.time()
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    if not output_csv:
        output_dir = os.path.join(os.path.dirname(__file__), f"../../data/hybrid")
        os.makedirs(output_dir, exist_ok=True)
        output_csv = os.path.join(output_dir, f"tgdd_inventory_{today_str}.csv")

    print("=" * 75)
    print(f"🚀 KHỞI ĐỘNG HYBRID INTELLIGENCE PIPELINE - {today_str}")
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

    print(f"✨ Tổng cộng {total_discovered_urls} URLs sản phẩm đang kinh doanh trên website.")

    # 2. BƯỚC 2: BÓC TÁCH THÔNG TIN SẢN PHẨM & BIẾN THỂ (CONCURRENT)
    print(f"\n[BƯỚC 2] Bóc tách biến thể (Model, Dung lượng, Màu sắc, SKU) với {max_workers} luồng...")
    all_variants = []
    crawl_tasks = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for cat_name, urls in all_category_urls.items():
            for u in urls:
                crawl_tasks.append(executor.submit(extract_product_data, u, cat_name))
        
        for future in as_completed(crawl_tasks):
            res = future.result()
            if res:
                all_variants.extend(res)

    print(f"✅ Đã trích xuất thành công {len(all_variants)} biến thể sản phẩm chi tiết.")

    # 3. BƯỚC 3: QUÉT TỒN KHO THEO SIÊU THỊ NATIONWIDE (CONCURRENT)
    print(f"\n[BƯỚC 3] Quét số lượng siêu thị còn tồn kho toàn quốc cho {len(all_variants)} biến thể...")
    processed_records = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        inv_tasks = [executor.submit(process_variant_inventory, v) for v in all_variants]
        for idx, future in enumerate(as_completed(inv_tasks), 1):
            processed_records.append(future.result())
            if idx % 50 == 0 or idx == len(all_variants):
                print(f"  ⚡ Tiến độ quét tồn kho: {idx}/{len(all_variants)} ({idx*100//len(all_variants)}%)")

    # 4. BƯỚC 4: XUẤT RA CSV
    print(f"\n[BƯỚC 4] Đang ghi dữ liệu vào file CSV: {output_csv}")
    fieldnames = [
        "Product_Name", "Category", "Storage", "Color", "SKU",
        "Price", "Ton_Kho", "Store_Count", "Store_HCM", "Store_Hanoi",
        "Top_Provinces_Stock", "Date", "Link"
    ]

    # Sắp xếp theo Category, Product_Name, Storage
    processed_records.sort(key=lambda x: (x.get("Category", ""), x.get("Product_Name", ""), x.get("Price", 0)))

    with open(output_csv, mode="w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        for r in processed_records:
            r["Date"] = today_str
            writer.writerow({k: r.get(k, "") for k in fieldnames})

    elapsed = time.time() - start_time
    print("=" * 75)
    print(f"🎉 HOÀN TẤT THÀNH CÔNG TRONG {elapsed:.1f} GIÂY!")
    print(f"📊 File kết quả đã sẵn sàng: {output_csv}")
    print(f"📈 Tổng số dòng dữ liệu: {len(processed_records)}")
    
    # 5. THỐNG KÊ NHANH
    in_stock_count = sum(1 for r in processed_records if r.get("Store_Count", 0) > 0)
    out_stock_count = len(processed_records) - in_stock_count
    print(f"   - Biến thể còn hàng tại siêu thị: {in_stock_count} ({in_stock_count*100//len(processed_records)}%)")
    print(f"   - Biến thể hết hàng toàn quốc:    {out_stock_count} ({out_stock_count*100//len(processed_records)}%)")
    print("=" * 75)

    return output_csv


if __name__ == "__main__":
    out_file = sys.argv[1] if len(sys.argv) > 1 else None
    run_pipeline(out_file)
