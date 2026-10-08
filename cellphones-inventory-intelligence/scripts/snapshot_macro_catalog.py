#!/usr/bin/env python3
"""
Macro Catalog Snapshot - CellphoneS Intelligence
================================================
Automated macro snapshot pipeline to scan all Apple products,
extract variants, prices, SMember tiers, and stock status.

Saves output to:
- data/raw/cps_catalog_{timestamp}.csv
- data/snapshots/cps_catalog_latest.json
"""

import argparse
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
logger = logging.getLogger("SnapshotMacro")


def run_snapshot(category_filter=None, province_id=config.DEFAULT_PROVINCE_ID):
    vn_tz = pytz.timezone("Asia/Ho_Chi_Minh")
    now_vn = datetime.now(vn_tz)
    timestamp_str = now_vn.strftime("%Y-%m-%d_%H%M")
    date_str = now_vn.strftime("%Y-%m-%d")

    logger.info(f"🚀 Starting CellphoneS Macro Snapshot at {now_vn.strftime('%Y-%m-%d %H:%M:%S')} (Province: {province_id})")

    # Load master slugs
    master_slugs_file = config.MASTER_DIR / "apple_product_slugs.json"
    with open(master_slugs_file, "r", encoding="utf-8") as f:
        master_slugs = json.load(f)

    client = CPSApiClient()
    all_records = []
    seen_product_ids = set()

    categories_to_run = [category_filter] if category_filter else list(master_slugs.keys())
    total_slugs_count = sum(len(master_slugs.get(c, [])) for c in categories_to_run)
    processed_count = 0

    for cat in categories_to_run:
        slugs = master_slugs.get(cat, [])
        logger.info(f"📂 Processing Category: {cat} ({len(slugs)} models)...")

        for slug in slugs:
            processed_count += 1
            try:
                state = client.fetch_product_nuxt_state(slug)
                if not state:
                    logger.warning(f"[{processed_count}/{total_slugs_count}] ⚠️ Failed to fetch state for {slug}")
                    continue

                product_id = state.get("productId")
                relations = state.get("productData", {}).get("general", {}).get("relation", [])
                variant_ids = [product_id] + [r for r in relations if r != product_id]

                # Fetch GraphQL variants for exact prices and stock flags
                variants_info = client.get_products_by_ids(variant_ids, province_id=province_id)

                for v in variants_info:
                    g = v.get("general", {})
                    pid = g.get("product_id")
                    if not pid or pid in seen_product_ids:
                        continue
                    seen_product_ids.add(pid)

                    f = v.get("filterable", {})
                    prices = f.get("prices", {})

                    stock_code = f.get("stock_available_id")
                    stock_label = config.STOCK_AVAILABLE_STATES.get(stock_code, f"Code {stock_code}")

                    record = {
                        "Snapshot_Date": date_str,
                        "Snapshot_Time": now_vn.strftime("%H:%M:%S"),
                        "Category": cat,
                        "Product_ID": pid,
                        "Product_Name": g.get("name"),
                        "Slug": g.get("url_path", "").replace(".html", ""),
                        "URL": f"{config.CPS_HOST}/{g.get('url_path', '')}",
                        "Gia_Niem_Yet": f.get("price"),
                        "Gia_Khuyen_Mai": f.get("special_price"),
                        "Gia_SNew": prices.get("snew", {}).get("value"),
                        "Gia_SMem": prices.get("smem", {}).get("value"),
                        "Gia_SVIP": prices.get("svip", {}).get("value"),
                        "Chiet_Khau_SMem": prices.get("smem", {}).get("chiet_khau", 0),
                        "Chiet_Khau_SVIP": prices.get("svip", {}).get("chiet_khau", 0),
                        "Stock_Code": stock_code,
                        "Stock_Status": stock_label,
                        "Is_In_Stock": (stock_code == 46),
                        "Company_Stock_ID": f.get("company_stock_id"),
                    }
                    all_records.append(record)

                if processed_count % 10 == 0 or processed_count == total_slugs_count:
                    logger.info(f"⚡ [{processed_count}/{total_slugs_count}] Collected {len(all_records)} unique SKUs...")

                time.sleep(0.05)  # Fast & polite spacing
            except Exception as e:
                logger.error(f"❌ Error processing {slug}: {e}")


    logger.info(f"✅ Extracted {len(all_records)} variant records.")

    if not all_records:
        logger.warning("No records collected.")
        return

    # Save to Raw CSV
    df = pd.DataFrame(all_records)
    csv_file = config.RAW_DIR / f"cps_catalog_{timestamp_str}.csv"
    latest_csv = config.RAW_DIR / "cps_catalog_latest.csv"
    df.to_csv(csv_file, index=False, encoding="utf-8-sig")
    df.to_csv(latest_csv, index=False, encoding="utf-8-sig")
    logger.info(f"💾 Saved Raw CSV: {csv_file}")

    # Save to Snapshot JSON
    snapshot_json = config.SNAPSHOTS_DIR / f"cps_snapshot_{timestamp_str}.json"
    latest_json = config.SNAPSHOTS_DIR / "cps_snapshot_latest.json"
    with open(snapshot_json, "w", encoding="utf-8") as f:
        json.dump(all_records, f, indent=2, ensure_ascii=False)
    with open(latest_json, "w", encoding="utf-8") as f:
        json.dump(all_records, f, indent=2, ensure_ascii=False)
    logger.info(f"💾 Saved Snapshot JSON: {snapshot_json}")

    # Print summary statistics
    print("\n" + "="*70)
    print("📊 BÁO CÁO TỔNG QUAN TỒN KHO CELLPHONES - DANH MỤC APPLE")
    print("="*70)
    total_skus = len(df)
    in_stock_skus = df[df["Is_In_Stock"] == True]
    in_stock_count = len(in_stock_skus)
    in_stock_pct = (in_stock_count / total_skus * 100) if total_skus > 0 else 0

    print(f"• Tổng số SKU Apple theo dõi : {total_skus}")
    print(f"• Số SKU còn hàng (Sẵn sàng) : {in_stock_count} ({in_stock_pct:.1f}%)")
    print(f"• Số SKU hết hàng/tạm hết    : {total_skus - in_stock_count} ({100 - in_stock_pct:.1f}%)")
    print("-" * 70)
    print("📌 Phân bổ theo ngành hàng:")
    cat_summary = df.groupby("Category").agg(
        Total_SKU=("Product_ID", "count"),
        In_Stock=("Is_In_Stock", lambda x: (x == True).sum()),
        Min_Price=("Gia_Khuyen_Mai", "min"),
        Max_Price=("Gia_Khuyen_Mai", "max")
    )
    cat_summary["Stock_Rate_%"] = (cat_summary["In_Stock"] / cat_summary["Total_SKU"] * 100).round(1)
    for cat_name, row in cat_summary.iterrows():
        min_p = f"{int(row['Min_Price']):,}₫" if pd.notnull(row['Min_Price']) and row['Min_Price'] > 0 else "N/A"
        max_p = f"{int(row['Max_Price']):,}₫" if pd.notnull(row['Max_Price']) and row['Max_Price'] > 0 else "N/A"
        print(f"  - {cat_name:<12}: {row['In_Stock']:>3}/{row['Total_SKU']:<3} SKU còn hàng ({row['Stock_Rate_%']:>5.1f}%) | Giá: {min_p} - {max_p}")

    print("-" * 70)
    print("📌 Phân bổ trạng thái kho (Stock Available State):")
    status_summary = df["Stock_Status"].value_counts()
    for status_name, count in status_summary.items():
        pct = (count / total_skus * 100)
        print(f"  - {status_name:<30}: {count:>3} SKU ({pct:>5.1f}%)")
    print("="*70 + "\n")



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Take macro snapshot of CellphoneS Apple catalog.")
    parser.add_argument("--category", choices=["iPhone", "iPad", "Mac", "Apple Watch", "AirPods"], default=None, help="Filter by category")
    parser.add_argument("--province", type=int, default=config.DEFAULT_PROVINCE_ID, help="Province ID (default: 30)")
    args = parser.parse_args()

    run_snapshot(category_filter=args.category, province_id=args.province)
