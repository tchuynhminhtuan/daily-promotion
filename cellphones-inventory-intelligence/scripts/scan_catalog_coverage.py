#!/usr/bin/env python3
"""
Catalog Coverage Scanner - CellphoneS Intelligence
===================================================
Automated high-performance scanner that measures real physical showroom
coverage and nationwide province availability for all products in the catalog.

Saves reports to:
- data/reports/cps_coverage_latest.csv
- data/reports/cps_coverage_latest.json
"""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import json
import logging
from pathlib import Path
import sys
import time
import pandas as pd
import pytz

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_DIR))
import config
from src.client import CPSApiClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("CoverageScanner")


def run_coverage_scan(category=None, province_id=config.DEFAULT_PROVINCE_ID, scan_all=False, max_workers=8):
    vn_tz = pytz.timezone("Asia/Ho_Chi_Minh")
    now_vn = datetime.now(vn_tz)
    timestamp_str = now_vn.strftime("%Y-%m-%d_%H%M")
    date_str = now_vn.strftime("%Y-%m-%d")

    province_name = config.PROVINCE_CODES.get(str(province_id), f"Tỉnh {province_id}")
    logger.info(f"🚀 Starting Real-Time Coverage Scan for {province_name} (ID: {province_id})...")

    # 1. Load Master Stores
    master_stores_file = config.MASTER_DIR / "cps_master_stores.json"
    total_province_stores = 70  # Default baseline for HCM
    if master_stores_file.exists():
        with open(master_stores_file, "r", encoding="utf-8") as f:
            all_stores = json.load(f)
        prov_stores = [s for s in all_stores if s.get("province_id") == province_id]
        if prov_stores:
            total_province_stores = len(prov_stores)
    logger.info(f"📍 Network baseline for {province_name}: {total_province_stores} physical showrooms.")

    # 2. Load Catalog Snapshot
    snapshot_file = config.SNAPSHOTS_DIR / "cps_snapshot_latest.json"
    if not snapshot_file.exists():
        logger.error(f"❌ Snapshot file not found: {snapshot_file}. Run snapshot_macro_catalog.py first!")
        return

    with open(snapshot_file, "r", encoding="utf-8") as f:
        catalog_items = json.load(f)

    # Filter by category if requested
    if category:
        catalog_items = [p for p in catalog_items if p.get("Category") == category]

    # Filter in-stock only unless scan_all is True
    if not scan_all:
        target_items = [p for p in catalog_items if p.get("Is_In_Stock") is True]
        logger.info(f"🔍 Filtering products: {len(target_items)} SKU có cờ tồn kho (Is_In_Stock == True).")
    else:
        target_items = catalog_items
        logger.info(f"🔍 Quét toàn bộ: {len(target_items)} SKU trong danh mục.")

    if not target_items:
        logger.warning("Không có sản phẩm nào phù hợp điều kiện lọc.")
        return

    client = CPSApiClient()

    # 3. Batch extract child_product IDs for target items via GraphQL
    logger.info(f"⚡ Đang lấy danh sách biến thể màu sắc (child_product) cho {len(target_items)} SKU...")
    product_ids = [str(p["Product_ID"]) for p in target_items]
    
    # Query in chunks of 50
    chunk_size = 50
    product_child_map = {}
    for i in range(0, len(product_ids), chunk_size):
        chunk = product_ids[i:i+chunk_size]
        ids_formatted = "[" + ", ".join(f'"{pid}"' for pid in chunk) + "]"
        query = f"""
query GetChildProducts {{
    products(filter: {{ static: {{ province_id: {province_id}, product_id: {ids_formatted} }} }}, size: {len(chunk)}) {{
        general {{
            product_id
            name
            child_product
        }}
    }}
}}
"""
        res = client.query_graphql(query)
        prods = res.get("data", {}).get("products", []) if res.get("data") else []
        for p in prods:
            g = p.get("general", {})
            pid = g.get("product_id")
            cids = g.get("child_product", []) or [pid]
            product_child_map[pid] = cids

    # 4. Batch query Nationwide Province Stock
    all_child_ids = set()
    for cids in product_child_map.values():
        all_child_ids.update(cids)
    all_child_list = list(all_child_ids)

    logger.info(f"🌍 Đang đối soát độ phủ toàn quốc cho {len(all_child_list)} biến thể con...")
    child_prov_stock = {}
    for i in range(0, len(all_child_list), 100):
        chunk_cids = all_child_list[i:i+100]
        p_res = client.get_instock_provinces(chunk_cids)
        child_prov_stock.update(p_res)

    # 5. Concurrent Query Store Stock for target province
    # Only query child IDs that have stock in province_id
    cids_in_province = []
    for cid in all_child_list:
        provs = child_prov_stock.get(str(cid), [])
        if any(p.get("province_id") == province_id for p in provs):
            cids_in_province.append(cid)

    logger.info(f"🏬 Có {len(cids_in_province)} biến thể con ghi nhận tồn kho tại {province_name}. Đang quét chi tiết showroom...")

    cid_shop_map = {}
    def fetch_shops(cid):
        res = client.get_shops_stock(cid, province_id=province_id)
        shops = []
        for d in res:
            for s in d.get("shops", []):
                shops.append(s)
        return cid, shops

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_shops, cid): cid for cid in cids_in_province}
        for fut in as_completed(futures):
            try:
                cid, shops = fut.result()
                cid_shop_map[cid] = shops
            except Exception as e:
                pass

    # 6. Aggregate Coverage by Product SKU
    coverage_records = []
    for item in target_items:
        pid = item["Product_ID"]
        cids = product_child_map.get(pid, [pid])

        # Nationwide province count
        active_provs = set()
        for cid in cids:
            for p in child_prov_stock.get(str(cid), []):
                active_provs.add(p.get("province_id"))
        
        nationwide_prov_count = len(active_provs)
        nationwide_cov_pct = round((nationwide_prov_count / 63.0) * 100, 1)

        # Local showroom count
        unique_shops = {}
        for cid in cids:
            for s in cid_shop_map.get(cid, []):
                unique_shops[s.get("id")] = s

        local_store_count = len(unique_shops)
        local_cov_pct = round((local_store_count / total_province_stores * 100), 1) if total_province_stores else 0

        # Tier classification
        if local_cov_pct >= 50:
            tier = "🟢 Dồi dào (>= 50%)"
        elif local_cov_pct >= 20:
            tier = "🟡 Trung bình (20 - 49%)"
        elif local_cov_pct > 0:
            tier = "🟠 Hạn chế (1 - 19%)"
        else:
            tier = "🔴 Cháy hàng / Ảo (0 store)"

        sample_addrs = "; ".join(s.get("address", "") for s in list(unique_shops.values())[:2])

        record = {
            "Scan_Date": date_str,
            "Scan_Time": now_vn.strftime("%H:%M:%S"),
            "Category": item.get("Category"),
            "Product_ID": pid,
            "Product_Name": item.get("Product_Name"),
            "Slug": item.get("Slug"),
            "Gia_Khuyen_Mai": item.get("Gia_Khuyen_Mai"),
            "Gia_SVIP": item.get("Gia_SVIP"),
            "Catalog_Stock_Code": item.get("Stock_Code"),
            "Nationwide_Provinces": nationwide_prov_count,
            "Nationwide_Coverage_Pct": nationwide_cov_pct,
            "Local_Store_Count": local_store_count,
            "Local_Total_Stores": total_province_stores,
            "Local_Store_Coverage_Pct": local_cov_pct,
            "Coverage_Tier": tier,
            "Sample_Stores": sample_addrs,
            "URL": item.get("URL"),
        }
        coverage_records.append(record)

    df_cov = pd.DataFrame(coverage_records)

    # 7. Save Reports
    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_csv = config.REPORTS_DIR / f"cps_coverage_{timestamp_str}.csv"
    latest_csv = config.REPORTS_DIR / "cps_coverage_latest.csv"
    latest_json = config.REPORTS_DIR / "cps_coverage_latest.json"

    df_cov.to_csv(report_csv, index=False, encoding="utf-8-sig")
    df_cov.to_csv(latest_csv, index=False, encoding="utf-8-sig")
    with open(latest_json, "w", encoding="utf-8") as f:
        json.dump(coverage_records, f, indent=2, ensure_ascii=False)

    logger.info(f"💾 Đã lưu báo cáo độ phủ CSV: {report_csv}")
    logger.info(f"💾 Đã lưu báo cáo độ phủ JSON: {latest_json}")

    # 8. Executive Summary Output
    print("\n" + "=" * 80)
    print(f"📊 BÁO CÁO TỔNG HỢP ĐỘ PHỦ TỒN KHO THỰC TẾ - CELLPHONES")
    print(f"📍 Khu vực: {province_name} | Thời gian: {now_vn.strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 80)

    total_scanned = len(df_cov)
    real_instock_df = df_cov[df_cov["Local_Store_Count"] > 0]
    real_instock_count = len(real_instock_df)
    phantom_stock_df = df_cov[(df_cov["Catalog_Stock_Code"] == 46) & (df_cov["Local_Store_Count"] == 0)]

    print(f"• Tổng số SKU quét độ phủ              : {total_scanned}")
    print(f"• Số SKU THỰC TẾ CÒN HÀNG tại showroom  : {real_instock_count} / {total_scanned} ({real_instock_count/total_scanned*100:.1f}%)")
    print(f"• Số SKU 'HÀNG ẢO / CACHE TĨNH' (Code 46 nhưng 0 store) : {len(phantom_stock_df)} SKU")
    print("-" * 80)

    print("📌 Phân bổ độ phủ Showroom theo Ngành Hàng:")
    cat_grp = df_cov.groupby("Category").agg(
        Total_SKU=("Product_ID", "count"),
        Real_InStock=("Local_Store_Count", lambda x: (x > 0).sum()),
        Avg_Store_Count=("Local_Store_Count", "mean"),
        Avg_Store_Coverage=("Local_Store_Coverage_Pct", "mean")
    )
    for cat_name, row in cat_grp.iterrows():
        print(f"  - {cat_name:<12}: {row['Real_InStock']:>2}/{row['Total_SKU']:<2} SKU thực có hàng | Đỗ phủ TB: {row['Avg_Store_Coverage']:>5.1f}% ({row['Avg_Store_Count']:.1f} showroom)")

    print("-" * 80)
    print("📌 Top 5 sản phẩm có độ phủ showroom cao nhất:")
    top_instock = df_cov.sort_values(by="Local_Store_Count", ascending=False).head(5)
    for _, row in top_instock.iterrows():
        price_fmt = f"{int(row['Gia_Khuyen_Mai']):,}₫" if pd.notnull(row['Gia_Khuyen_Mai']) and row['Gia_Khuyen_Mai'] > 0 else "N/A"
        print(f"  • {row['Product_Name'][:38]:<38} | {row['Local_Store_Count']:>2}/{total_province_stores} store ({row['Local_Store_Coverage_Pct']:>4.1f}%) | {price_fmt}")

    if len(phantom_stock_df) > 0:
        print("-" * 80)
        print("🚨 CẢNH BÁO: Phát hiện sản phẩm dính Cache Ảo (Catalog ghi Code 46 nhưng 0 Showroom):")
        for _, row in phantom_stock_df.head(5).iterrows():
            print(f"  ⚠️ {row['Product_Name'][:45]:<45} (Toàn quốc: {row['Nationwide_Provinces']} tỉnh, TP.HCM: 0 store)")

    print("=" * 80 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scan real-time physical store coverage across catalog.")
    parser.add_argument("--province", type=int, default=config.DEFAULT_PROVINCE_ID, help="Province ID (default: 30)")
    parser.add_argument("--category", choices=["iPhone", "iPad", "Mac", "Apple Watch", "AirPods"], default=None, help="Filter category")
    parser.add_argument("--all", action="store_true", help="Scan all catalog SKUs, not just in-stock items")
    parser.add_argument("--workers", type=int, default=8, help="Concurrent workers")
    args = parser.parse_args()

    run_coverage_scan(category=args.category, province_id=args.province, scan_all=args.all, max_workers=args.workers)
