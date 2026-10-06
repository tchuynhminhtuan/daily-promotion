"""
Core Hybrid Crawler & Inventory Scanner for Thế Giới Di Động (Apple Ecosystem)
Tích hợp: Category Discovery + Schema.org JSON-LD + Affordability & Trade-in + Store-level API.
"""

import os
import sys
import re
import json
import csv
import time
import argparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Set, Tuple

import requests
from bs4 import BeautifulSoup

from ..config import (
    CATEGORIES,
    STORE_API_URL,
    HEADERS,
    HYBRID_DATA_DIR,
    PROJECT_ROOT
)


def parse_storage_and_specs(product_name: str, category: str) -> str:
    """Trích xuất cấu hình bộ nhớ / RAM / kích thước viền phù hợp theo danh mục."""
    name = product_name.strip()

    if category == "MacBook":
        match = re.search(r'(\d+GB\s*/\s*\d+(?:GB|TB)(?:/\w+)?)', name, re.IGNORECASE)
        if match:
            return match.group(1).replace(" ", "")
        m_ram = re.search(r'(\d+GB)', name, re.IGNORECASE)
        m_ssd = re.search(r'(\d+(?:GB|TB))', name, re.IGNORECASE)
        if m_ram and m_ssd:
            return f"{m_ram.group(1)}/{m_ssd.group(1)}"

    elif category == "Apple Watch":
        match = re.search(r'(\d{2}mm)', name, re.IGNORECASE)
        if match:
            return match.group(1)

    match_cap = re.search(r'\b(\d+\s*(?:GB|TB))\b', name, re.IGNORECASE)
    if match_cap:
        return match_cap.group(1).replace(" ", "")

    return "Standard"


def discover_category_links(cat_name: str, cat_url: str) -> List[str]:
    """Quét trang danh mục để tìm toàn bộ URL sản phẩm đang kinh doanh."""
    try:
        resp = requests.get(cat_url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, 'html.parser')
        urls: Set[str] = set()

        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith('/'):
                href = f"https://www.thegioididong.com{href}"
            
            if href.startswith('https://www.thegioididong.com/'):
                clean_url = href.split('?')[0].split('#')[0]
                if any(clean_url.startswith(f"https://www.thegioididong.com/{prefix}/") for prefix in [
                    "dtdd", "laptop", "dong-ho-thong-minh", "may-tinh-bang", "tai-nghe"
                ]):
                    if not any(x in clean_url for x in ["/tin-tuc", "/hoi-dap", "/game-app", "/so-sanh"]):
                        urls.add(clean_url)

        return sorted(list(urls))
    except Exception as e:
        print(f"❌ Lỗi khi quét {cat_name}: {e}")
        return []


def parse_affordability(soup: BeautifulSoup, price: int) -> Dict[str, Any]:
    """Bóc tách các chỉ số Affordability, Trợ giá thu cũ đổi mới, Trả góp 0%, và Ưu đãi tài chính."""
    res = {
        "Direct_Discount_VND": 0,
        "Accessory_Voucher_VND": 0,
        "Trade_In_Subsidy_VND": 0,
        "Bank_Cashback_VND": 0,
        "Installment_0_Percent": False,
        "Min_Monthly_Payment_12M": 0,
        "Affordability_Effective_Price": price,
        "Affordability_Programs": []
    }
    
    promo_block = soup.select_one('.block__promo, .pr-item')
    promo_text = promo_block.get_text(separator=' | ', strip=True) if promo_block else ''
    full_text = soup.get_text(separator=' ', strip=True)
    
    # 1. Giảm giá trực tiếp
    m_direct = re.search(r'Giảm giá\s+([\d.,]+)\s*đ', promo_text, re.I)
    if m_direct:
        val = int(m_direct.group(1).replace('.', '').replace(',', ''))
        res["Direct_Discount_VND"] = val
        res["Affordability_Programs"].append(f"Giảm trực tiếp {val:,}đ")

    # 2. Phiếu mua hàng phụ kiện
    m_vouch = re.search(r'Phiếu mua hàng[^\d]+([\d.,]+)\s*đ', promo_text, re.I)
    if m_vouch:
        val = int(m_vouch.group(1).replace('.', '').replace(',', ''))
        res["Accessory_Voucher_VND"] = val
        res["Affordability_Programs"].append(f"Voucher phụ kiện {val:,}đ")

    # 3. Trợ giá thu cũ đổi mới (Trade-In Subsidy)
    m_trade = re.search(r'Thu cũ đổi mới[^\d]+([\d.,]+)\s*đ', promo_text, re.I)
    if not m_trade:
        m_trade = re.search(r'thu cũ trợ giá đến\s+([\d.,]+)\s*([trm]+)', full_text, re.I)
    if m_trade:
        matched_str = m_trade.group(0)
        if 'đ' in matched_str or 'vnđ' in matched_str.lower():
            val = int(m_trade.group(1).replace('.', '').replace(',', ''))
        else:
            val = int(float(m_trade.group(1).replace(',', '.')) * 1e6)
        res["Trade_In_Subsidy_VND"] = val
        res["Affordability_Programs"].append(f"Trợ giá thu cũ đổi mới {val:,}đ")

    # 4. Hoàn tiền mở thẻ ngân hàng đối tác
    m_bank = re.search(r'hoàn\s+(?:ngay\s+)?đến\s+([\d.,]+)\s*đ', promo_text, re.I)
    if m_bank:
        val = int(m_bank.group(1).replace('.', '').replace(',', ''))
        res["Bank_Cashback_VND"] = val
        res["Affordability_Programs"].append(f"Hoàn tiền mở thẻ {val:,}đ")

    # 5. Trả chậm / Trả góp 0%
    if re.search(r'trả (?:chậm|góp)\s+0%', full_text, re.I):
        res["Installment_0_Percent"] = True
        res["Affordability_Programs"].append("Trả chậm 0% lãi suất")

    # 6. Tính toán giá thực tế & số tiền trả mỗi tháng (12M kỳ hạn chuẩn)
    net_price = max(0, price - res["Direct_Discount_VND"])
    res["Min_Monthly_Payment_12M"] = round(net_price / 12) if net_price > 0 else 0
    res["Affordability_Effective_Price"] = max(0, net_price - res["Trade_In_Subsidy_VND"])

    return res


def extract_product_data(product_url: str, category: str) -> List[Dict[str, Any]]:
    """Bóc tách thông tin chi tiết và tất cả biến thể của sản phẩm từ JSON-LD & DOM."""
    try:
        resp = requests.get(product_url, headers=HEADERS, timeout=12)
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, 'html.parser')
        h1 = soup.find('h1')
        main_title = h1.get_text(strip=True) if h1 else ""
        if not main_title:
            return []

        description = ""
        rating_score = None
        rating_count = None
        promotions = []

        for promo_el in soup.find_all(['div', 'li', 'p']):
            txt = promo_el.get_text(strip=True)
            if any(k in txt.lower() for k in ['thu cũ đổi mới', 'trả chậm 0%', 'giảm thêm', 'phiếu mua hàng', 'quà tặng']) and 10 < len(txt) < 120:
                if txt not in promotions:
                    promotions.append(txt)

        variants = []
        for s in soup.find_all('script'):
            txt = s.get_text().strip()
            
            # 1. ProductGroup (Đa biến thể)
            if 'ProductGroup' in txt and 'hasVariant' in txt:
                try:
                    data = json.loads(txt)
                    if data.get('@type') == 'ProductGroup' and 'hasVariant' in data:
                        description = data.get('description', '')
                        agg_rating = data.get('aggregateRating', {})
                        rating_score = agg_rating.get('ratingValue')
                        rating_count = agg_rating.get('ratingCount')

                        for v in data['hasVariant']:
                            sku = str(v.get('sku', '')).strip()
                            name = v.get('name', main_title).strip()
                            color = v.get('color', '').strip() or 'Default'
                            price_raw = v.get('offers', {}).get('price', 0)
                            price = int(float(price_raw)) if price_raw else 0
                            
                            storage = parse_storage_and_specs(name, category)
                            affordability = parse_affordability(soup, price)

                            variants.append({
                                "Product_Name": name,
                                "Category": category,
                                "Storage": storage,
                                "Color": color,
                                "SKU": sku,
                                "Gia_Niem_Yet": price,
                                "Gia_Khuyen_Mai": price,
                                "Direct_Discount_VND": affordability["Direct_Discount_VND"],
                                "Trade_In_Subsidy_VND": affordability["Trade_In_Subsidy_VND"],
                                "Min_Monthly_Payment_12M": affordability["Min_Monthly_Payment_12M"],
                                "Installment_0_Percent": affordability["Installment_0_Percent"],
                                "Affordability_Effective_Price": affordability["Affordability_Effective_Price"],
                                "Affordability": affordability,
                                "Description": description,
                                "Rating_Score": rating_score,
                                "Rating_Count": rating_count,
                                "Promotions": promotions[:5],
                                "Link": product_url
                            })
                        break
                except:
                    pass
            
            # 2. Single Product
            elif '\"@type\":\"Product\"' in txt or '\"@type\": \"Product\"' in txt:
                try:
                    data = json.loads(txt)
                    if data.get('@type') == 'Product':
                        sku = str(data.get('sku', '')).strip()
                        name = data.get('name', main_title).strip()
                        price_raw = data.get('offers', {}).get('price', 0)
                        price = int(float(price_raw)) if price_raw else 0
                        storage = parse_storage_and_specs(name, category)
                        description = data.get('description', '')
                        affordability = parse_affordability(soup, price)

                        variants.append({
                            "Product_Name": name,
                            "Category": category,
                            "Storage": storage,
                            "Color": "Default",
                            "SKU": sku,
                            "Gia_Niem_Yet": price,
                            "Gia_Khuyen_Mai": price,
                            "Direct_Discount_VND": affordability["Direct_Discount_VND"],
                            "Trade_In_Subsidy_VND": affordability["Trade_In_Subsidy_VND"],
                            "Min_Monthly_Payment_12M": affordability["Min_Monthly_Payment_12M"],
                            "Installment_0_Percent": affordability["Installment_0_Percent"],
                            "Affordability_Effective_Price": affordability["Affordability_Effective_Price"],
                            "Affordability": affordability,
                            "Description": description,
                            "Rating_Score": None,
                            "Rating_Count": None,
                            "Promotions": promotions[:5],
                            "Link": product_url
                        })
                        break
                except:
                    pass

        return variants
    except Exception:
        return []


def query_store_inventory_deep(sku: str) -> Dict[str, Any]:
    """Truy vấn tồn kho chi tiết tới từng cửa hàng và máy mẫu trưng bày."""
    if not sku:
        return {
            "total_stores": 0,
            "store_hcm": 0,
            "store_hn": 0,
            "top_provinces_str": "",
            "province_breakdown": {},
            "sample_quantity_total": 0,
            "store_list": []
        }

    payload = {
        "productCode": str(sku),
        "provinceId": 0,
        "wardId": 0,
        "isDelivery": False,
        "haveStock": True,
        "haveStore": True,
        "siteId": 2
    }

    try:
        resp = requests.post(
            STORE_API_URL,
            headers={**HEADERS, "Content-Type": "application/json"},
            json=payload,
            timeout=8
        )
        if resp.status_code == 200:
            res_data = resp.json()
            if res_data.get("code") == 0 and res_data.get("data"):
                items = res_data["data"]
                total = len(items)

                store_hcm = 0
                store_hn = 0
                sample_qty_total = 0
                province_counts: Dict[str, int] = {}
                store_list: List[Dict[str, Any]] = []

                for s in items:
                    p_name = s.get("provinceName", "Khác")
                    province_counts[p_name] = province_counts.get(p_name, 0) + 1
                    
                    if "Hồ Chí Minh" in p_name:
                        store_hcm += 1
                    elif "Hà Nội" in p_name:
                        store_hn += 1

                    sample_qty = s.get("sampleDisplayQuantity", 0) or 0
                    sample_qty_total += sample_qty

                    store_list.append({
                        "store_id": s.get("storeId"),
                        "store_name": s.get("storeName"),
                        "address": s.get("address"),
                        "ward": s.get("wardName"),
                        "province": p_name,
                        "is_in_stock": s.get("isInStock", False),
                        "sample_display_quantity": sample_qty,
                        "google_map_link": s.get("googleMapLink")
                    })

                top_sorted = sorted(province_counts.items(), key=lambda x: x[1], reverse=True)[:3]
                top_str = ", ".join([f"{k}: {v}" for k, v in top_sorted])

                return {
                    "total_stores": total,
                    "store_hcm": store_hcm,
                    "store_hn": store_hn,
                    "top_provinces_str": top_str,
                    "province_breakdown": province_counts,
                    "sample_quantity_total": sample_qty_total,
                    "store_list": store_list
                }
    except Exception:
        pass

    return {
        "total_stores": 0,
        "store_hcm": 0,
        "store_hn": 0,
        "top_provinces_str": "",
        "province_breakdown": {},
        "sample_quantity_total": 0,
        "store_list": []
    }


def process_variant_inventory(variant: Dict[str, Any]) -> Dict[str, Any]:
    sku = variant.get("SKU", "")
    inv = query_store_inventory_deep(sku)

    item = dict(variant)
    count = inv["total_stores"]
    item["Ton_Kho"] = "Yes" if count > 0 else "No"
    item["Store_Count"] = count
    item["Store_HCM"] = inv["store_hcm"]
    item["Store_Hanoi"] = inv["store_hn"]
    item["Top_Provinces_Stock"] = inv["top_provinces_str"]

    item["Sample_Display_Total"] = inv["sample_quantity_total"]
    item["Province_Breakdown"] = inv["province_breakdown"]
    item["Detailed_Stores"] = inv["store_list"]

    return item


def run_pipeline(output_csv: str = None, output_json: str = None, sync_raw: bool = False, max_workers: int = 12) -> Tuple[str, str]:
    start_time = time.time()
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    timestamp_str = now.strftime("%Y-%m-%d_%H%M")
    
    os.makedirs(HYBRID_DATA_DIR, exist_ok=True)

    if not output_csv:
        output_csv = os.path.join(HYBRID_DATA_DIR, f"tgdd_inventory_{timestamp_str}.csv")
    if not output_json:
        output_json = os.path.join(HYBRID_DATA_DIR, f"tgdd_inventory_deep_{timestamp_str}.json")

    print("=" * 75)
    print(f"🚀 KHỞI ĐỘNG RETAIL INTELLIGENCE PIPELINE - {timestamp_str}")
    print("=" * 75)

    print("\n[BƯỚC 1] Tự động quét 5 danh mục Apple trên Thế Giới Di Động...")
    all_category_urls = {}
    total_discovered_urls = 0
    
    for cat_name, cat_url in CATEGORIES.items():
        urls = discover_category_links(cat_name, cat_url)
        all_category_urls[cat_name] = urls
        total_discovered_urls += len(urls)
        print(f"  📁 {cat_name:<12}: Tìm thấy {len(urls)} URLs")

    print(f"✨ Tổng cộng {total_discovered_urls} URLs sản phẩm đang niêm yết.")

    print(f"\n[BƯỚC 2] Bóc tách biến thể & Affordability với {max_workers} luồng...")
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

    print(f"\n[BƯỚC 3] Quét tồn kho chi tiết cho {len(unique_variants)} biến thể...")
    processed_records = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        inv_tasks = [executor.submit(process_variant_inventory, v) for v in unique_variants]
        for idx, future in enumerate(as_completed(inv_tasks), 1):
            processed_records.append(future.result())
            if idx % 50 == 0 or idx == len(unique_variants):
                print(f"  ⚡ Tiến độ: {idx}/{len(unique_variants)} ({idx*100//len(unique_variants)}%)")

    processed_records.sort(key=lambda x: (x.get("Category", ""), x.get("Product_Name", ""), x.get("Gia_Khuyen_Mai", 0)))

    # Ghi JSON
    print(f"\n[BƯỚC 4.1] Đang ghi dữ liệu phân tích sâu vào file JSON: {output_json}")
    json_payload = {
        "metadata": {
            "source": "thegioididong.com",
            "crawl_date": today_str,
            "generated_at": datetime.now().isoformat(),
            "total_products_discovered": total_discovered_urls,
            "total_unique_variants": len(processed_records),
            "in_stock_variants_count": sum(1 for r in processed_records if r.get("Store_Count", 0) > 0),
            "out_of_stock_variants_count": sum(1 for r in processed_records if r.get("Store_Count", 0) == 0)
        },
        "data": processed_records
    }
    with open(output_json, mode="w", encoding="utf-8") as jf:
        json.dump(json_payload, jf, ensure_ascii=False, indent=2)

    # Ghi CSV
    print(f"[BƯỚC 4.2] Đang ghi dữ liệu bảng phẳng vào file CSV: {output_csv}")
    csv_fields = [
        "Product_Name", "Category", "Storage", "Color", "SKU",
        "Gia_Niem_Yet", "Gia_Khuyen_Mai",
        "Direct_Discount_VND", "Trade_In_Subsidy_VND", "Min_Monthly_Payment_12M",
        "Installment_0_Percent", "Affordability_Effective_Price",
        "Ton_Kho", "Store_Count", "Store_HCM", "Store_Hanoi",
        "Top_Provinces_Stock", "Date", "Link"
    ]
    with open(output_csv, mode="w", encoding="utf-8-sig", newline="") as cf:
        writer = csv.DictWriter(cf, fieldnames=csv_fields, delimiter=";")
        writer.writeheader()
        for r in processed_records:
            r["Date"] = today_str
            writer.writerow({k: r.get(k, "") for k in csv_fields})

    # Cập nhật alias
    try:
        import shutil
        latest_json = os.path.join(HYBRID_DATA_DIR, "tgdd_inventory_deep_latest.json")
        daily_json = os.path.join(HYBRID_DATA_DIR, f"tgdd_inventory_deep_{today_str}.json")
        latest_csv = os.path.join(HYBRID_DATA_DIR, "tgdd_inventory_latest.csv")
        daily_csv = os.path.join(HYBRID_DATA_DIR, f"tgdd_inventory_{today_str}.csv")
        
        if os.path.abspath(output_json) != os.path.abspath(latest_json):
            shutil.copyfile(output_json, latest_json)
        if os.path.abspath(output_json) != os.path.abspath(daily_json):
            shutil.copyfile(output_json, daily_json)
        if os.path.abspath(output_csv) != os.path.abspath(latest_csv):
            shutil.copyfile(output_csv, latest_csv)
        if os.path.abspath(output_csv) != os.path.abspath(daily_csv):
            shutil.copyfile(output_csv, daily_csv)
    except Exception as e:
        print(f"⚠️ Lưu ý sao chép latest/daily alias: {e}")

    # Đồng bộ raw data
    if sync_raw:
        raw_dir = os.path.join(PROJECT_ROOT, f"data/raw/{today_str}")
        os.makedirs(raw_dir, exist_ok=True)
        raw_csv_path = os.path.join(raw_dir, f"2-mw-{today_str}.csv")
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
    print(f"📊 1. File JSON sâu: {output_json} (Dung lượng: ~{os.path.getsize(output_json)//1024} KB)")
    print(f"📊 2. File CSV phẳng: {output_csv}")
    print(f"📈 Tổng số bản ghi duy nhất: {len(processed_records)}")
    in_stock_count = sum(1 for r in processed_records if r.get("Store_Count", 0) > 0)
    out_stock_count = len(processed_records) - in_stock_count
    print(f"   - Biến thể còn hàng tại siêu thị: {in_stock_count} ({in_stock_count*100//len(processed_records)}%)")
    print(f"   - Biến thể hết hàng toàn quốc:    {out_stock_count} ({out_stock_count*100//len(processed_records)}%)")
    print("=" * 75)

    return output_csv, output_json


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TGDD Hybrid Crawler & Deep Stock Scanner")
    parser.add_argument("--output", "-o", help="Đường dẫn file CSV xuất ra", default=None)
    parser.add_argument("--json", "-j", help="Đường dẫn file JSON xuất ra", default=None)
    parser.add_argument("--sync-raw", action="store_true", help="Đồng bộ sang data/raw/YYYY-MM-DD/2-mw-YYYY-MM-DD.csv")
    parser.add_argument("--workers", "-w", type=int, default=12, help="Số luồng xử lý song song")
    args = parser.parse_args()

    run_pipeline(output_csv=args.output, output_json=args.json, sync_raw=args.sync_raw, max_workers=args.workers)
