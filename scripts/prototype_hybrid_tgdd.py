#!/usr/bin/env python3
"""
Prototype Hybrid Scraper & Inventory Scanner for Thế Giới Di Động (TGDD)
Tính năng:
1. Tự động phát hiện danh sách URL sản phẩm Apple trên TGDD (Discovery)
2. So sánh tìm Link Mới và Link Cũ bị loại bỏ/ngừng kinh doanh
3. Bóc tách toàn bộ biến thể (Dung lượng, Màu sắc, Giá, Mã SKU/ProductCode)
4. Quét số lượng cửa hàng còn tồn kho trên toàn quốc cho từng biến thể
"""

import os
import re
import json
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Any

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Origin': 'https://www.thegioididong.com',
    'Referer': 'https://www.thegioididong.com/',
    'Content-Type': 'application/json'
}

STORE_API_URL = "https://api.thegioididong.com/gw/bus-tgdd-tmdt/api/Store/GetStoreByDeliveryPolicy"


def discover_category_links(category_url: str = "https://www.thegioididong.com/dtdd-apple-iphone") -> List[str]:
    """Tự động phát hiện các link sản phẩm đang hiển thị trong danh mục."""
    resp = requests.get(category_url, headers=HEADERS, timeout=15)
    if resp.status_code != 200:
        raise Exception(f"Không thể tải danh mục: {resp.status_code}")
    
    soup = BeautifulSoup(resp.text, 'html.parser')
    links = set()
    for a in soup.find_all('a', href=True):
        href = a['href']
        if '/dtdd/iphone-' in href:
            clean = href.split('?')[0].split('#')[0]
            if not clean.startswith('http'):
                clean = 'https://www.thegioididong.com' + clean
            links.add(clean)
    return sorted(list(links))


def extract_product_variants(product_url: str) -> Dict[str, Any]:
    """
    Trích xuất:
    - Tên sản phẩm chính
    - Danh sách biến thể (SKU code, Dung lượng, Màu sắc, Giá niêm yết/khuyến mãi)
    """
    resp = requests.get(product_url, headers=HEADERS, timeout=15)
    if resp.status_code != 200:
        return {"status": "error", "http_code": resp.status_code, "url": product_url}

    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # 1. Tên sản phẩm (H1)
    h1 = soup.find('h1')
    main_title = h1.get_text(strip=True) if h1 else ""

    # 2. Tìm Schema.org JSON-LD ProductGroup
    variants = []
    scripts = soup.find_all('script')
    for s in scripts:
        txt = s.get_text().strip()
        if 'ProductGroup' in txt and 'hasVariant' in txt:
            try:
                data = json.loads(txt)
                if data.get('@type') == 'ProductGroup' and 'hasVariant' in data:
                    for v in data['hasVariant']:
                        sku = v.get('sku', '')
                        name = v.get('name', '')
                        color = v.get('color', '')
                        price = v.get('offers', {}).get('price', 0)
                        availability = v.get('offers', {}).get('availability', '')
                        is_in_stock = "InStock" in availability

                        # Tách dung lượng từ name (vd: iPhone 17 256GB -> 256GB)
                        storage_match = re.search(r'(\d+(?:GB|TB))', name, re.IGNORECASE)
                        storage = storage_match.group(1) if storage_match else "Default"

                        variants.append({
                            "sku": str(sku),
                            "name": name,
                            "storage": storage,
                            "color": color,
                            "price": int(price) if price else 0,
                            "in_stock_schema": is_in_stock
                        })
                    break
            except Exception:
                continue

    return {
        "status": "success",
        "url": product_url,
        "title": main_title,
        "variants": variants
    }


def scan_store_inventory(sku: str, province_id: int = 0) -> Dict[str, Any]:
    """
    Quét tồn kho trực tiếp từ hệ thống Thế Giới Di Động:
    - province_id = 0: Quét toàn quốc
    - province_id cụ thể (vd: 1027 là TP.HCM, 3 là Hà Nội)
    """
    payload = {
        "productCode": str(sku),
        "provinceId": province_id,
        "wardId": 0,
        "haveStock": True,
        "haveStore": True,
        "siteId": 2
    }
    try:
        r = requests.post(STORE_API_URL, json=payload, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            res_data = r.json().get('data', {})
            total_stores = res_data.get('total', 0)
            store_list = res_data.get('storeList', [])
            
            # Thống kê theo tỉnh thành
            province_breakdown = {}
            for store in store_list:
                p_name = store.get('provinceName', 'Khác')
                province_breakdown[p_name] = province_breakdown.get(p_name, 0) + 1

            return {
                "sku": sku,
                "total_stores_in_stock": total_stores,
                "province_breakdown": province_breakdown,
                "sample_stores": [
                    {
                        "store_name": s.get('additionalInfoValue'),
                        "address": s.get('webAddress'),
                        "province": s.get('provinceName')
                    } for s in store_list[:3]
                ]
            }
    except Exception as e:
        return {"sku": sku, "error": str(e), "total_stores_in_stock": 0}

    return {"sku": sku, "total_stores_in_stock": 0}


def run_experiment(target_url: str):
    print("=" * 70)
    print("🚀 BẮT ĐẦU THỬ NGHIỆM HỆ THỐNG LAI CHO THẾ GIỚI DI ĐỘNG")
    print("=" * 70)

    # 1. Thử nghiệm trích xuất sản phẩm & biến thể
    print(f"\n[1] Đang phân tích URL sản phẩm mục tiêu: {target_url}")
    prod_data = extract_product_variants(target_url)
    
    if prod_data["status"] != "success":
        print(f"❌ Không tải được dữ liệu: {prod_data}")
        return

    print(f"✅ Tên sản phẩm: {prod_data['title']}")
    print(f"✅ Số lượng biến thể phát hiện: {len(prod_data['variants'])}")
    print("-" * 70)

    # 2. Quét tồn kho theo từng biến thể
    print(f"\n[2] Đang quét số lượng shop còn tồn kho trên toàn quốc theo từng biến thể...")
    results = []
    for idx, v in enumerate(prod_data["variants"], 1):
        sku = v["sku"]
        inv = scan_store_inventory(sku, province_id=0)
        
        v_info = {
            "name": v["name"],
            "storage": v["storage"],
            "color": v["color"],
            "price": f"{v['price']:,} đ",
            "sku": sku,
            "total_shops_in_stock": inv["total_stores_in_stock"],
            "top_provinces": list(inv.get("province_breakdown", {}).items())[:3]
        }
        results.append(v_info)
        
        print(f"  [{idx}/{len(prod_data['variants'])}] {v['name']} | Màu: {v['color']:<18} | SKU: {sku} | Giá: {v_info['price']}")
        print(f"       -> 🏪 Còn hàng tại: {inv['total_stores_in_stock']} shop toàn quốc!")
        if inv.get("province_breakdown"):
            top_p = ", ".join([f"{k}: {val} shop" for k, val in list(inv["province_breakdown"].items())[:3]])
            print(f"       -> 📍 Phân bổ: {top_p}")

    # 3. Thử nghiệm Discovery: So sánh danh mục với link hiện tại
    print("\n" + "=" * 70)
    print("[3] Thử nghiệm tính năng TỰ ĐỘNG PHÁT HIỆN SẢN PHẨM MỚI (Discovery)")
    print("=" * 70)
    
    # Giả định tập link hiện tại trong sites.py (lấy mẫu vài link)
    from utils.sites import total_links
    existing_mw_links = set(total_links.get("mw_urls", []))
    print(f"Số lượng link MW hiện có trong sites.py: {len(existing_mw_links)}")
    
    discovered_links = set(discover_category_links())
    print(f"Số lượng link iPhone quét được từ trang danh mục TGDD: {len(discovered_links)}")
    
    new_links = discovered_links - existing_mw_links
    print(f"\n✨ PHÁT HIỆN {len(new_links)} LINK MỚI CHƯA CÓ TRONG sites.py:")
    for nl in sorted(list(new_links))[:10]:
        print(f"  + [MỚI] {nl}")
    if len(new_links) > 10:
        print(f"  ... và {len(new_links) - 10} link khác.")


if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.thegioididong.com/dtdd/iphone-17?code=0131491004682"
    # Ensure sys.path allows importing utils.sites
    sys.path.append(os.path.join(os.path.dirname(__file__), "../src/crawlers"))
    run_experiment(url)
