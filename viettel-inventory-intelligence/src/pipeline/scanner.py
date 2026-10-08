"""
Viettel Store Multi-Threaded Inventory Scanner
==============================================
Orchestrates parallel scanning of Viettel Store products across the Apple ecosystem,
extracting exact stock quantities, ERP variant details, and store-level breakdown.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import json
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import sys

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(PROJECT_DIR))
import config
from src.client import ViettelStoreClient
from src.models import ProductInfo

logger = logging.getLogger("ViettelScanner")


class ViettelScanner:
    def __init__(self, concurrency: int = 6, timeout: int = 15):
        self.concurrency = concurrency
        self.client = ViettelStoreClient(timeout=timeout)

    @staticmethod
    def extract_pid_from_url(url: str) -> Optional[str]:
        """Extract PID from ViettelStore URL (e.g. pid339614.html -> 339614)."""
        match = re.search(r"pid(\d+)", url, re.IGNORECASE)
        return match.group(1) if match else None

    def scan_catalog(
        self,
        target_items: List[Dict[str, str]],
        include_stores: bool = True,
        save_snapshot: bool = True,
    ) -> List[ProductInfo]:
        """
        Scan a list of target items (dictionaries with 'product_id' or 'url').
        target_items can be [{'product_id': '339614', 'name': 'iPhone 16 128GB'}] or list of URLs.
        """
        results: List[ProductInfo] = []
        total = len(target_items)
        logger.info(f"Starting inventory scan for {total} Viettel Store items with concurrency={self.concurrency}")

        def _worker(item: Dict[str, str]) -> Optional[ProductInfo]:
            pid = item.get("product_id")
            url = item.get("url", "")
            if not pid and url:
                pid = self.extract_pid_from_url(url)
            if not pid:
                return None

            name = item.get("name") or item.get("product_name") or f"Viettel PID {pid}"
            cat_group = item.get("category_group") or item.get("category") or ""
            try:
                info = self.client.probe_product(
                    product_id=pid,
                    product_name=name,
                    category_group=cat_group,
                    url=url,
                    include_stores=include_stores,
                )
                return info
            except Exception as e:
                logger.error(f"Error scanning PID {pid}: {e}")
                return None

        with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
            future_to_item = {executor.submit(_worker, it): it for it in target_items}
            completed = 0
            for future in as_completed(future_to_item):
                completed += 1
                try:
                    res = future.result()
                    if res:
                        results.append(res)
                        status_str = f"Stock: {res.total_nationwide_stock} pcs" if res.has_physical_stock else "Out of stock"
                        print(f"[{completed}/{total}] [{res.category_group or 'Apple'}] PID {res.product_id} ({res.product_name[:30]}): {status_str} | Variants: {len(res.variants)}")
                except Exception as e:
                    logger.error(f"Worker exception: {e}")

        if save_snapshot and results:
            self.save_snapshots(results)

        return results

    def save_snapshots(self, products: List[ProductInfo]) -> Tuple[Path, Path]:
        """Save scan results as structured JSON and flattened CSV."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        json_path = config.SNAPSHOTS_DIR / f"viettel_inventory_{timestamp}.json"
        json_latest = config.SNAPSHOTS_DIR / "viettel_inventory_latest.json"
        csv_latest = config.REPORTS_DIR / "viettel_inventory_latest.csv"

        # 1. Save JSON
        data = [p.to_dict() for p in products]
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        with open(json_latest, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 2. Save Flattened CSV (One row per variant)
        rows = []
        for p in products:
            for v in p.variants:
                store_codes = ",".join([s.store_code for s in v.stores_in_stock])
                rows.append({
                    "Product_ID": p.product_id,
                    "Product_Name": p.product_name,
                    "Category_Group": p.category_group or p.category,
                    "Color_Name": v.color_name,
                    "Rule_ID": v.rule_id,
                    "ERP_Product_ID": v.erp_product_id,
                    "Spec_Code": v.spec_code,
                    "Gia_Niem_Yet": v.price,
                    "Gia_Ban_Thuc_Te": v.sell_price,
                    "Ton_Kho_Tong": v.amount_in_stock,
                    "Trang_Thai_Ban": "Bình thường" if v.sale_state == 0 else ("Hết hàng" if v.sale_state == 1 else "Pre-Order"),
                    "So_Sieu_Thi_Co_Hang": len(v.stores_in_stock),
                    "Danh_Sach_Sieu_Thi": store_codes,
                    "URL": p.url,
                    "Last_Updated": p.last_updated
                })

        if rows:
            with open(csv_latest, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)

        print(f"\nSaved snapshots:")
        print(f" - JSON: {json_latest}")
        print(f" - CSV:  {csv_latest}")
        return json_latest, csv_latest
