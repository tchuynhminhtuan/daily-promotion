#!/usr/bin/env python3
"""
[05] Map Viettel Store Crawled Supermarkets to Personnel Tree
==============================================================
Fuses crawled Viettel Store inventory locations with the official
Cluster Personnel Tree (Apple Store ID / POSM ID mapping).
Extracts store managers, cluster personnel, Apple experts, and indexes
all physical inventory available at each individual store.

Generates:
  - data/master/viettel_store_mapping.json (Bản đồ ánh xạ mã siêu thị)
  - data/reports/viettel_store_inventory_viewer.html (Viewer giao diện tra cứu)
"""

import json
import logging
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Project path
PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_DIR))
import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ViettelStoreMapper")


def normalize_address(text: str) -> str:
    """Normalize Vietnamese address string for robust token matching."""
    if not text:
        return ""
    # Normalize unicode to decomposed form then remove combining marks
    text = unicodedata.normalize("NFD", text)
    text = re.sub(r"[\u0300-\u036f]", "", text)
    text = text.lower()
    # Replace separators with spaces
    text = re.sub(r"[^\w\s]", " ", text)
    tokens = text.split()
    # Common stop-words in Vietnamese administrative addresses
    stop_words = {
        "so", "nha", "duong", "pho", "phuong", "quan", "huyen",
        "thi", "xa", "thanh", "tinh", "tp", "tt", "p", "q", "h",
        "to", "dan", "khu", "ap", "thon", "xom"
    }
    filtered = [t for t in tokens if t not in stop_words]
    return " ".join(filtered)


def extract_numbers(text: str) -> Set[str]:
    """Extract street/house numbers from an address (e.g. '291-293' -> {'291', '293'})."""
    if not text:
        return set()
    nums = re.findall(r"\b\d+\b", text)
    return set(nums)


def load_personnel_tree_stores(tree_path: Path) -> List[Dict[str, Any]]:
    """Extract all Viettel channel stores from cluster_personnel_tree.json."""
    with open(tree_path, "r", encoding="utf-8") as f:
        tree = json.load(f)

    vt_stores = []

    def _traverse(obj: Any, current_cluster: str = ""):
        if isinstance(obj, dict):
            c_name = obj.get("cluster_name") or current_cluster or obj.get("name", "")
            if "stores_detail" in obj and isinstance(obj["stores_detail"], list):
                for s in obj["stores_detail"]:
                    chanel = str(s.get("chanel_code", "")).upper()
                    s_name = str(s.get("store_name", "")).upper()
                    if "VIETTEL" in chanel or "VIETTEL" in s_name:
                        store_copy = dict(s)
                        store_copy["cluster_name"] = c_name
                        store_copy["norm_raw"] = normalize_address(s.get("store_address_raw", ""))
                        store_copy["norm_name"] = normalize_address(s.get("store_name", ""))
                        full_addr = f"{s.get('store_address', '')} {s.get('store_ward', '')} {s.get('store_district', '')} {s.get('store_province', '')}"
                        store_copy["norm_full_addr"] = normalize_address(full_addr)
                        store_copy["numbers"] = extract_numbers(s.get("store_address_raw", ""))
                        vt_stores.append(store_copy)

            for k, v in obj.items():
                if k != "stores_detail":
                    _traverse(v, c_name if len(c_name) > 1 else current_cluster)
        elif isinstance(obj, list):
            for it in obj:
                _traverse(it, current_cluster)

    _traverse(tree)
    # Deduplicate by store_code if any
    unique_stores = {}
    for s in vt_stores:
        code = s.get("store_code")
        if code and code not in unique_stores:
            unique_stores[code] = s
        elif not code:
            unique_stores[f"id_{len(unique_stores)}"] = s

    logger.info(f"Loaded {len(unique_stores)} unique Viettel stores from Personnel Tree.")
    return list(unique_stores.values())


def load_crawled_stores_and_inventory(snapshot_path: Path) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
    """
    Extract all unique store addresses from crawled snapshot and invert inventory by store.
    Returns:
      (crawled_stores, store_inventory_map)
    """
    with open(snapshot_path, "r", encoding="utf-8") as f:
        products = json.load(f)

    crawled_stores = {}
    store_inventory = defaultdict(list)

    for p in products:
        pid = p.get("product_id")
        pname = p.get("product_name")
        pcat = p.get("category_group") or p.get("category") or "Apple"
        purl = p.get("url")

        for v in p.get("variants", []):
            color = v.get("color_name")
            price = v.get("sell_price") or v.get("price") or 0
            original_price = v.get("price") or price
            rule_id = v.get("rule_id")
            erp_id = v.get("erp_product_id")

            item_summary = {
                "product_id": pid,
                "product_name": pname,
                "category": pcat,
                "color_name": color,
                "price": price,
                "original_price": original_price,
                "rule_id": rule_id,
                "erp_product_id": erp_id,
                "url": purl,
            }

            for s in v.get("stores_in_stock", []):
                addr = s.get("address")
                vt_code = s.get("store_code")
                prov_code = s.get("province_code")

                if not addr:
                    continue

                if addr not in crawled_stores:
                    crawled_stores[addr] = {
                        "vt_code": vt_code,
                        "province_code": prov_code,
                        "address": addr,
                        "norm_addr": normalize_address(addr),
                        "numbers": extract_numbers(addr),
                        "sku_count": 0,
                    }

                crawled_stores[addr]["sku_count"] += 1
                store_inventory[addr].append(item_summary)

    logger.info(f"Extracted {len(crawled_stores)} unique supermarket locations from inventory.")
    return crawled_stores, store_inventory


def match_stores(personnel_stores: List[Dict[str, Any]], crawled_stores: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Match Personnel Tree stores to Crawled Supermarkets via weighted token & numeric overlap.
    """
    matched_results = []
    crawled_matched_set = set()

    for p in personnel_stores:
        best_match_addr = None
        best_match_info = None
        best_score = 0.0

        p_words = set(p["norm_full_addr"].split())
        p_nums = p["numbers"]
        p_prov = normalize_address(p.get("store_province", ""))
        p_dist = normalize_address(p.get("store_district", ""))

        for c_addr, c_info in crawled_stores.items():
            c_words = set(c_info["norm_addr"].split())
            c_nums = c_info["numbers"]

            # Overlap tokens
            common_words = p_words.intersection(c_words)
            score = len(common_words) / max(1, len(p_words))

            # Number match bonus (street numbers)
            common_nums = p_nums.intersection(c_nums)
            if common_nums:
                score += 0.35

            # Province & District bonus
            if p_prov and p_prov in c_info["norm_addr"]:
                score += 0.20
            if p_dist and p_dist in c_info["norm_addr"]:
                score += 0.15

            if score > best_score:
                best_score = score
                best_match_addr = c_addr
                best_match_info = c_info

        is_matched = best_score >= 0.50
        matched_crawled_addr = best_match_addr if is_matched else ""
        if is_matched and best_match_addr:
            crawled_matched_set.add(best_match_addr)

        matched_results.append({
            "apple_store_code": p.get("store_code", ""),
            "store_id": p.get("store_id", ""),
            "store_name": p.get("store_name", ""),
            "cluster_name": p.get("cluster_name", ""),
            "area_code": p.get("area_code", ""),
            "personnel_address_raw": p.get("store_address_raw", ""),
            "province": p.get("store_province", ""),
            "district": p.get("store_district", ""),
            "experts": p.get("expert", []),
            "managers": p.get("manager", []),
            "is_matched": is_matched,
            "match_score": round(best_score, 2),
            "vt_store_code": best_match_info.get("vt_code", "") if is_matched else "",
            "vt_province_code": best_match_info.get("province_code", "") if is_matched else "",
            "crawled_address": matched_crawled_addr,
        })

    matched_count = sum(1 for m in matched_results if m["is_matched"])
    logger.info(f"Store Matching Result: {matched_count} / {len(personnel_stores)} matched ({matched_count/len(personnel_stores):.1%})")
    return matched_results


def generate_viewer_html(
    matched_stores: List[Dict[str, Any]],
    crawled_stores: Dict[str, Dict[str, Any]],
    store_inventory: Dict[str, List[Dict[str, Any]]],
    output_html_path: Path
):
    """
    Generate interactive standalone HTML viewer matching fpt_store_inventory_viewer.html design.
    """
    # Build store master table for the viewer
    viewer_stores = []
    # 1. First add all personnel stores (matched & unmatched)
    for s in matched_stores:
        c_addr = s.get("crawled_address", "")
        inv = store_inventory.get(c_addr, [])
        viewer_stores.append({
            "appleStoreCode": s["apple_store_code"],
            "vtStoreCode": s.get("vt_store_code") or s["apple_store_code"],
            "storeName": s["store_name"],
            "cluster": s["cluster_name"] or "Miền Bắc / Khác",
            "area": s["area_code"] or "Viettel",
            "province": s["province"] or "Toàn quốc",
            "district": s["district"] or "",
            "address": c_addr or s["personnel_address_raw"],
            "personnelAddress": s["personnel_address_raw"],
            "experts": s["experts"],
            "managers": s["managers"],
            "isMatched": s["is_matched"],
            "matchScore": s["match_score"],
            "stockItemCount": len(inv),
            "crawledAddress": c_addr,
        })

    # 2. Also append remaining crawled supermarkets not in personnel tree
    matched_addrs = {s.get("crawled_address") for s in matched_stores if s.get("crawled_address")}
    for c_addr, c_info in crawled_stores.items():
        if c_addr not in matched_addrs:
            inv = store_inventory.get(c_addr, [])
            viewer_stores.append({
                "appleStoreCode": c_info["vt_code"] or "VT_SUPER",
                "vtStoreCode": c_info["vt_code"],
                "storeName": f"Viettel Store {c_info['vt_code']} - {c_info['province_code']}",
                "cluster": "Mở rộng (Chưa gán Cụm Apple)",
                "area": c_info["province_code"],
                "province": c_info["province_code"],
                "district": "",
                "address": c_addr,
                "personnelAddress": "",
                "experts": [],
                "managers": [],
                "isMatched": False,
                "matchScore": 0.0,
                "stockItemCount": len(inv),
                "crawledAddress": c_addr,
            })

    # Prepare inventory dictionary indexed by appleStoreCode and vtStoreCode
    inv_by_code = {}
    for vs in viewer_stores:
        code = vs["appleStoreCode"]
        c_addr = vs["crawledAddress"]
        inv_by_code[code] = store_inventory.get(c_addr, [])

    # Sort stores so matched with stock come first
    viewer_stores.sort(key=lambda x: (x["stockItemCount"] > 0, x["isMatched"], x["stockItemCount"]), reverse=True)

    json_stores = json.dumps(viewer_stores, ensure_ascii=False)
    json_inventory = json.dumps(inv_by_code, ensure_ascii=False)

    html_template = f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Viettel Store Inventory Intelligence - Tra Cứu Tồn Kho Theo Apple Store ID & Cụm Nhân Sự</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-primary: #080c14;
      --bg-secondary: #0f172a;
      --card-bg: rgba(17, 24, 39, 0.82);
      --card-border: rgba(255, 255, 255, 0.09);
      --accent-viettel: #ee0033;
      --accent-viettel-glow: rgba(238, 0, 51, 0.25);
      --accent-apple: #38bdf8;
      --accent-amber: #f59e0b;
      --accent-green: #10b981;
      --accent-purple: #8b5cf6;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --glass-blur: blur(20px);
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }}

    body {{
      background-color: var(--bg-primary);
      color: var(--text-main);
      padding: 24px;
      min-height: 100vh;
      background-image: 
        radial-gradient(at 0% 0%, rgba(238, 0, 51, 0.16) 0px, transparent 50%),
        radial-gradient(at 100% 0%, rgba(56, 189, 248, 0.14) 0px, transparent 50%),
        radial-gradient(at 50% 100%, rgba(139, 92, 246, 0.09) 0px, transparent 60%);
      background-attachment: fixed;
    }}

    .container {{
      max-width: 1460px;
      margin: 0 auto;
    }}

    /* Header */
    header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 20px;
      border-bottom: 1px solid var(--card-border);
      margin-bottom: 24px;
      flex-wrap: wrap;
      gap: 12px;
    }}

    .brand-title {{
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }}

    .badge-viettel {{
      background: linear-gradient(135deg, #ee0033, #c4002a);
      color: white;
      font-weight: 800;
      font-size: 13px;
      padding: 6px 14px;
      border-radius: 8px;
      letter-spacing: 0.5px;
      box-shadow: 0 4px 14px var(--accent-viettel-glow);
    }}

    .badge-apple {{
      background: rgba(56, 189, 248, 0.16);
      border: 1px solid rgba(56, 189, 248, 0.4);
      color: #38bdf8;
      font-weight: 700;
      font-size: 13px;
      padding: 6px 14px;
      border-radius: 8px;
    }}

    h1 {{
      font-size: 22px;
      font-weight: 800;
      letter-spacing: -0.5px;
    }}

    /* Preset Bar */
    .preset-bar {{
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 16px;
      flex-wrap: wrap;
    }}

    .preset-label {{
      font-size: 13px;
      color: var(--text-muted);
      font-weight: 600;
    }}

    .preset-chip {{
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--card-border);
      color: var(--text-main);
      padding: 6px 12px;
      border-radius: 8px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }}

    .preset-chip:hover {{
      background: rgba(238, 0, 51, 0.2);
      border-color: #ee0033;
      color: #ff4d6d;
    }}

    /* Control Panel */
    .control-panel {{
      background: var(--card-bg);
      backdrop-filter: var(--glass-blur);
      border: 1px solid var(--card-border);
      border-radius: 18px;
      padding: 20px;
      margin-bottom: 24px;
      display: grid;
      grid-template-columns: 2.2fr 1.2fr 2fr auto;
      gap: 16px;
      align-items: center;
      position: relative;
    }}

    .search-wrapper {{
      position: relative;
      width: 100%;
    }}

    .search-input, .select-box {{
      width: 100%;
      background: rgba(11, 17, 32, 0.95);
      border: 1px solid var(--card-border);
      color: var(--text-main);
      padding: 12px 16px;
      border-radius: 10px;
      font-size: 14px;
      outline: none;
      transition: border-color 0.2s, box-shadow 0.2s;
    }}

    .search-input:focus, .select-box:focus {{
      border-color: #ee0033;
      box-shadow: 0 0 0 3px rgba(238, 0, 51, 0.2);
    }}

    .autocomplete-list {{
      position: absolute;
      top: calc(100% + 6px);
      left: 0;
      right: 0;
      background: #111827;
      border: 1px solid var(--card-border);
      border-radius: 12px;
      max-height: 320px;
      overflow-y: auto;
      z-index: 1000;
      box-shadow: 0 16px 36px rgba(0, 0, 0, 0.6);
      display: none;
    }}

    .autocomplete-item {{
      padding: 10px 14px;
      font-size: 13px;
      cursor: pointer;
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}

    .autocomplete-item:hover {{
      background: rgba(238, 0, 51, 0.15);
      color: #ff4d6d;
    }}

    .btn-search {{
      background: linear-gradient(135deg, #ee0033, #c4002a);
      color: white;
      border: none;
      padding: 12px 20px;
      border-radius: 10px;
      font-weight: 700;
      cursor: pointer;
      transition: opacity 0.2s;
    }}

    .btn-search:hover {{
      opacity: 0.9;
    }}

    /* Store Info Card */
    .store-hero {{
      background: var(--card-bg);
      backdrop-filter: var(--glass-blur);
      border: 1px solid var(--card-border);
      border-radius: 18px;
      padding: 24px;
      margin-bottom: 24px;
      display: grid;
      grid-template-columns: 1.8fr 1.2fr;
      gap: 24px;
    }}

    .store-title {{
      font-size: 20px;
      font-weight: 800;
      margin-bottom: 8px;
      color: #fff;
    }}

    .store-address {{
      font-size: 14px;
      color: var(--text-muted);
      line-height: 1.5;
      margin-bottom: 12px;
    }}

    .store-tags {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }}

    .tag {{
      font-size: 12px;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: 6px;
    }}

    .tag-cluster {{ background: rgba(139, 92, 246, 0.18); border: 1px solid rgba(139, 92, 246, 0.4); color: #c084fc; }}
    .tag-area {{ background: rgba(16, 185, 129, 0.18); border: 1px solid rgba(16, 185, 129, 0.4); color: #34d399; }}
    .tag-match {{ background: rgba(56, 189, 248, 0.18); border: 1px solid rgba(56, 189, 248, 0.4); color: #38bdf8; }}
    .tag-erp {{ background: rgba(245, 158, 11, 0.18); border: 1px solid rgba(245, 158, 11, 0.4); color: #fbbf24; }}

    /* Personnel Box */
    .personnel-box {{
      background: rgba(11, 17, 32, 0.7);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 16px;
    }}

    .personnel-header {{
      font-size: 13px;
      font-weight: 700;
      color: var(--accent-amber);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 10px;
      display: flex;
      align-items: center;
      gap: 6px;
    }}

    .personnel-list {{
      display: flex;
      flex-direction: column;
      gap: 8px;
      max-height: 140px;
      overflow-y: auto;
    }}

    .personnel-item {{
      font-size: 13px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 6px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }}

    .personnel-name {{ font-weight: 600; color: #fff; }}
    .personnel-contact {{ font-size: 12px; color: var(--text-muted); }}

    /* Category Filter & Stats */
    .filter-bar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
      flex-wrap: wrap;
      gap: 12px;
    }}

    .category-pills {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }}

    .pill-btn {{
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--card-border);
      color: var(--text-muted);
      padding: 8px 14px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }}

    .pill-btn:hover, .pill-btn.active {{
      background: rgba(238, 0, 51, 0.2);
      border-color: #ee0033;
      color: #fff;
    }}

    .stats-summary {{
      font-size: 14px;
      font-weight: 700;
      color: #fff;
    }}

    /* Table */
    .table-container {{
      background: var(--card-bg);
      backdrop-filter: var(--glass-blur);
      border: 1px solid var(--card-border);
      border-radius: 18px;
      overflow: hidden;
      box-shadow: 0 12px 32px rgba(0, 0, 0, 0.4);
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      text-align: left;
    }}

    th {{
      background: rgba(11, 17, 32, 0.95);
      padding: 16px;
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--text-muted);
      border-bottom: 1px solid var(--card-border);
    }}

    td {{
      padding: 14px 16px;
      font-size: 14px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.04);
      vertical-align: middle;
    }}

    tr:hover td {{
      background: rgba(255, 255, 255, 0.02);
    }}

    .product-name-cell {{
      font-weight: 600;
      color: #fff;
    }}

    .badge-stock {{
      background: rgba(16, 185, 129, 0.16);
      color: #34d399;
      border: 1px solid rgba(16, 185, 129, 0.4);
      padding: 4px 8px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 700;
      display: inline-block;
    }}

    .price-text {{
      font-weight: 700;
      color: #ff4d6d;
    }}

    .btn-link {{
      color: #38bdf8;
      text-decoration: none;
      font-size: 12px;
      font-weight: 600;
    }}
    .btn-link:hover {{ text-decoration: underline; }}

    .empty-state {{
      padding: 48px;
      text-align: center;
      color: var(--text-muted);
    }}

    @media (max-width: 1024px) {{
      .control-panel {{ grid-template-columns: 1fr; }}
      .store-hero {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="brand-title">
        <span class="badge-viettel">VIETTEL STORE</span>
        <span class="badge-apple">APPLE ECOSYSTEM</span>
        <h1>Tra Cứu Tồn Kho Thực Tế Theo Apple Store ID & Cụm Nhân Sự</h1>
      </div>
      <div style="font-size: 13px; color: var(--text-muted);">
        Dữ liệu quét ERP thời gian thực: <strong>Tháng 10/2026</strong>
      </div>
    </header>

    <!-- Quick Presets -->
    <div class="preset-bar">
      <span class="preset-label">⚡ Cửa Hàng Tiêu Biểu:</span>
      <button class="preset-chip" onclick="selectStore('1472727')">Bắc Ninh (1472727 - BNH01)</button>
      <button class="preset-chip" onclick="selectStore('1472726')">Từ Sơn (1472726 - BNH02)</button>
      <button class="preset-chip" onclick="selectStore('1615834')">Minh Khai Từ Sơn (1615834)</button>
      <button class="preset-chip" onclick="selectStore('1472836')">Hưng Yên (1472836 - HYN01)</button>
      <button class="preset-chip" onclick="selectStore('HNI09')">498 Xã Đàn - Hà Nội</button>
      <button class="preset-chip" onclick="selectStore('HNI03')">Ngọc Khánh - Hà Nội</button>
      <button class="preset-chip" onclick="selectStore('DNG08')">Đà Nẵng (DNG08)</button>
    </div>

    <!-- Control Panel -->
    <div class="control-panel">
      <div class="search-wrapper">
        <input type="text" id="searchInput" class="search-input" placeholder="🔍 Tìm theo Apple ID (1472727), Mã Viettel (BNH01), Tên đường, Chuyên viên..." autocomplete="off">
        <div id="autocompleteList" class="autocomplete-list"></div>
      </div>

      <select id="clusterSelect" class="select-box">
        <option value="ALL">Tất cả Cụm / Cluster</option>
      </select>

      <select id="storeDropdown" class="select-box">
        <!-- populated dynamically -->
      </select>

      <button class="btn-search" onclick="applySearch()">Xem Tồn Kho</button>
    </div>

    <!-- Store Hero -->
    <div class="store-hero">
      <div>
        <div id="storeTitle" class="store-title">Đang tải thông tin cửa hàng...</div>
        <div id="storeAddress" class="store-address">...</div>
        <div id="storeTags" class="store-tags"></div>
      </div>

      <div class="personnel-box">
        <div class="personnel-header">👥 Nhân Sự Phụ Trách & Quản Lý Cụm</div>
        <div id="personnelList" class="personnel-list"></div>
      </div>
    </div>

    <!-- Category Filter Bar -->
    <div class="filter-bar">
      <div class="category-pills" id="categoryPills">
        <button class="pill-btn active" data-cat="ALL">Tất cả (<span id="countAll">0</span>)</button>
        <button class="pill-btn" data-cat="iPhone">iPhone (<span id="countIphone">0</span>)</button>
        <button class="pill-btn" data-cat="iPad">iPad (<span id="countIpad">0</span>)</button>
        <button class="pill-btn" data-cat="Apple Watch">Apple Watch (<span id="countWatch">0</span>)</button>
        <button class="pill-btn" data-cat="AirPods">AirPods (<span id="countAirpods">0</span>)</button>
        <button class="pill-btn" data-cat="Apple Pencil">Pencil & PK (<span id="countPencil">0</span>)</button>
        <button class="pill-btn" data-cat="Sạc Cáp Apple">Sạc Cáp (<span id="countCharger">0</span>)</button>
        <button class="pill-btn" data-cat="Ốp Lưng Apple">Ốp Lưng (<span id="countCase">0</span>)</button>
      </div>

      <div class="stats-summary" id="statsSummary">
        Hiển thị 0 mặt hàng còn tại cửa hàng
      </div>
    </div>

    <!-- Inventory Table -->
    <div class="table-container">
      <table>
        <thead>
          <tr>
            <th style="width: 32%;">Tên Sản Phẩm</th>
            <th style="width: 14%;">Màu Sắc</th>
            <th style="width: 14%;">Danh Mục</th>
            <th style="width: 14%;">Giá Bán Viettel</th>
            <th style="width: 14%;">Trạng Thái Kho</th>
            <th style="width: 12%;">Thao Tác</th>
          </tr>
        </thead>
        <tbody id="inventoryTableBody">
          <!-- populated dynamically -->
        </tbody>
      </table>
      <div id="emptyState" class="empty-state" style="display: none;">
        Không tìm thấy sản phẩm nào đang còn hàng tại siêu thị này theo bộ lọc.
      </div>
    </div>
  </div>

  <script>
    // Embedded Data
    const storesData = {json_stores};
    const inventoryData = {json_inventory};

    let currentStoreCode = "";
    let currentCategory = "ALL";

    // Initialize clusters
    const clusters = new Set();
    storesData.forEach(s => {{ if (s.cluster) clusters.add(s.cluster); }});
    const clusterSelect = document.getElementById("clusterSelect");
    Array.from(clusters).sort().forEach(c => {{
      const opt = document.createElement("option");
      opt.value = c;
      opt.textContent = c;
      clusterSelect.appendChild(opt);
    }});

    function populateStoreDropdown(filteredCluster = "ALL") {{
      const dd = document.getElementById("storeDropdown");
      dd.innerHTML = "";
      const list = filteredCluster === "ALL" 
        ? storesData 
        : storesData.filter(s => s.cluster === filteredCluster);

      list.forEach(s => {{
        const opt = document.createElement("option");
        opt.value = s.appleStoreCode;
        const matchedBadge = s.isMatched ? "✅ " : "📍 ";
        opt.textContent = `${{matchedBadge}}[${{s.appleStoreCode}}] ${{s.storeName}} (${{s.stockItemCount}} SKU)`;
        dd.appendChild(opt);
      }});

      if (list.length > 0) {{
        currentStoreCode = list[0].appleStoreCode;
        loadStore(currentStoreCode);
      }}
    }}

    function selectStore(code) {{
      const found = storesData.find(s => s.appleStoreCode === code || s.vtStoreCode === code);
      if (found) {{
        currentStoreCode = found.appleStoreCode;
        document.getElementById("storeDropdown").value = currentStoreCode;
        loadStore(currentStoreCode);
        window.location.hash = `#${{currentStoreCode}}`;
      }}
    }}

    function loadStore(storeCode) {{
      const store = storesData.find(s => s.appleStoreCode === storeCode || s.vtStoreCode === storeCode);
      if (!store) return;
      currentStoreCode = store.appleStoreCode;

      // Update Hero
      document.getElementById("storeTitle").innerHTML = `${{store.storeName}} <span style="font-size: 14px; color: var(--accent-amber); font-weight: 700;">(Mã Apple ID: ${{store.appleStoreCode}})</span>`;
      document.getElementById("storeAddress").textContent = store.address || store.personnelAddress;

      const tagsContainer = document.getElementById("storeTags");
      tagsContainer.innerHTML = `
        <span class="tag tag-cluster">Cụm: ${{store.cluster}}</span>
        <span class="tag tag-area">Vùng: ${{store.area}}</span>
        <span class="tag tag-erp">Mã Viettel ERP: ${{store.vtStoreCode}}</span>
        <span class="tag tag-match">${{store.isMatched ? "Khớp bản đồ: 100%" : "Siêu thị mở rộng"}}</span>
      `;

      // Update Personnel
      const pList = document.getElementById("personnelList");
      pList.innerHTML = "";
      if (store.experts && store.experts.length > 0) {{
        store.experts.forEach(exp => {{
          const div = document.createElement("div");
          div.className = "personnel-item";
          div.innerHTML = `
            <div>
              <span class="personnel-name">⭐ ${{exp.name}}</span>
              <span style="font-size: 11px; color: var(--accent-apple); margin-left: 4px;">(Apple Expert)</span>
            </div>
            <div class="personnel-contact">${{exp.phone || ""}} · ${{exp.email || ""}}</div>
          `;
          pList.appendChild(div);
        }});
      }}
      if (store.managers && store.managers.length > 0) {{
        store.managers.forEach(mgr => {{
          if (mgr.name && mgr.name !== "N/A") {{
            const div = document.createElement("div");
            div.className = "personnel-item";
            div.innerHTML = `
              <div>
                <span class="personnel-name">👔 ${{mgr.name}}</span>
                <span style="font-size: 11px; color: var(--accent-amber); margin-left: 4px;">(Quản lý)</span>
              </div>
              <div class="personnel-contact">${{mgr.phone || ""}}</div>
            `;
            pList.appendChild(div);
          }}
        }});
      }}
      if ((!store.experts || store.experts.length === 0) && (!store.managers || store.managers.length === 0)) {{
        pList.innerHTML = `<div style="font-size: 12px; color: var(--text-muted);">Chưa có thông tin nhân sự Apple phụ trách tại điểm này.</div>`;
      }}

      // Load items
      const items = inventoryData[storeCode] || inventoryData[store.appleStoreCode] || [];
      renderInventoryTable(items);
    }}

    function renderInventoryTable(items) {{
      const tbody = document.getElementById("inventoryTableBody");
      tbody.innerHTML = "";

      // Count categories
      const counts = {{
        ALL: items.length,
        iPhone: 0,
        iPad: 0,
        "Apple Watch": 0,
        AirPods: 0,
        "Apple Pencil": 0,
        "Sạc Cáp Apple": 0,
        "Ốp Lưng Apple": 0,
      }};

      items.forEach(it => {{
        const c = it.category;
        if (c.includes("iPhone")) counts.iPhone++;
        else if (c.includes("iPad")) counts.iPad++;
        else if (c.includes("Watch")) counts["Apple Watch"]++;
        else if (c.includes("AirPods")) counts.AirPods++;
        else if (c.includes("Pencil")) counts["Apple Pencil"]++;
        else if (c.includes("Sạc") || c.includes("Cáp")) counts["Sạc Cáp Apple"]++;
        else if (c.includes("Ốp")) counts["Ốp Lưng Apple"]++;
      }});

      document.getElementById("countAll").textContent = counts.ALL;
      document.getElementById("countIphone").textContent = counts.iPhone;
      document.getElementById("countIpad").textContent = counts.iPad;
      document.getElementById("countWatch").textContent = counts["Apple Watch"];
      document.getElementById("countAirpods").textContent = counts.AirPods;
      document.getElementById("countPencil").textContent = counts["Apple Pencil"];
      document.getElementById("countCharger").textContent = counts["Sạc Cáp Apple"];
      document.getElementById("countCase").textContent = counts["Ốp Lưng Apple"];

      // Filter by category
      let filtered = items;
      if (currentCategory !== "ALL") {{
        filtered = items.filter(it => it.category.toLowerCase().includes(currentCategory.toLowerCase()));
      }}

      document.getElementById("statsSummary").textContent = `Hiển thị ${{filtered.length}} / ${{items.length}} mặt hàng còn sẵn`;

      if (filtered.length === 0) {{
        document.getElementById("emptyState").style.display = "block";
        return;
      }}
      document.getElementById("emptyState").style.display = "none";

      filtered.forEach(it => {{
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td class="product-name-cell">
            ${{it.product_name}}
            <div style="font-size: 11px; color: var(--text-muted); font-weight: 400; margin-top: 2px;">PID: ${{it.product_id}} | ERP: ${{it.erp_product_id || "N/A"}}</div>
          </td>
          <td>${{it.color_name || "Mặc định"}}</td>
          <td><span style="font-size: 12px; color: var(--accent-apple); font-weight: 600;">${{it.category}}</span></td>
          <td class="price-text">${{Number(it.price).toLocaleString("vi-VN")}} ₫</td>
          <td><span class="badge-stock">🟢 Còn hàng tại shop</span></td>
          <td><a href="${{it.url}}" target="_blank" class="btn-link">Xem Viettel ↗</a></td>
        `;
        tbody.appendChild(tr);
      }});
    }}

    // Autocomplete Search
    const searchInput = document.getElementById("searchInput");
    const autoList = document.getElementById("autocompleteList");

    searchInput.addEventListener("input", (e) => {{
      const q = e.target.value.trim().toLowerCase();
      if (!q) {{
        autoList.style.display = "none";
        return;
      }}

      const matches = storesData.filter(s => 
        s.appleStoreCode.toLowerCase().includes(q) ||
        s.vtStoreCode.toLowerCase().includes(q) ||
        s.storeName.toLowerCase().includes(q) ||
        (s.address && s.address.toLowerCase().includes(q)) ||
        (s.experts && s.experts.some(exp => exp.name.toLowerCase().includes(q)))
      ).slice(0, 10);

      autoList.innerHTML = "";
      if (matches.length === 0) {{
        autoList.style.display = "none";
        return;
      }}

      matches.forEach(m => {{
        const div = document.createElement("div");
        div.className = "autocomplete-item";
        div.innerHTML = `
          <div>
            <strong>[${{m.appleStoreCode}}]</strong> ${{m.storeName}}
            <div style="font-size: 11px; color: var(--text-muted);">${{m.address}}</div>
          </div>
          <span style="font-size: 11px; color: #34d399; font-weight: 700;">${{m.stockItemCount}} SKU</span>
        `;
        div.onclick = () => {{
          selectStore(m.appleStoreCode);
          autoList.style.display = "none";
          searchInput.value = `[${{m.appleStoreCode}}] ${{m.storeName}}`;
        }};
        autoList.appendChild(div);
      }});
      autoList.style.display = "block";
    }});

    document.addEventListener("click", (e) => {{
      if (!e.target.closest(".search-wrapper")) autoList.style.display = "none";
    }});

    function applySearch() {{
      const val = document.getElementById("storeDropdown").value;
      if (val) selectStore(val);
    }}

    // Category pills click
    document.querySelectorAll(".pill-btn").forEach(btn => {{
      btn.addEventListener("click", () => {{
        document.querySelectorAll(".pill-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        currentCategory = btn.getAttribute("data-cat");
        const items = inventoryData[currentStoreCode] || [];
        renderInventoryTable(items);
      }});
    }});

    // Cluster dropdown change
    clusterSelect.addEventListener("change", (e) => {{
      populateStoreDropdown(e.target.value);
    }});

    // Store dropdown change
    document.getElementById("storeDropdown").addEventListener("change", (e) => {{
      selectStore(e.target.value);
    }});

    // Hash navigation
    function handleHash() {{
      const hash = window.location.hash.replace("#", "").trim();
      if (hash) {{
        selectStore(hash);
      }}
    }}

    // Start
    populateStoreDropdown("ALL");
    handleHash();
    if (!window.location.hash) {{
      selectStore("1472727"); // Default to Bac Ninh hot store
    }}
  </script>
</body>
</html>
"""

    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write(html_template)

    logger.info(f"Generated Viettel Store Inventory Viewer at: {output_html_path}")


def main():
    print("=" * 80)
    print("🚀 [BƯỚC 05] ĐỐI SOÁT VÀ ÁNH XẠ CỬA HÀNG VIETTEL VÀO PERSONNEL TREE")
    print("=" * 80)

    tree_path = config.MASTER_DIR / "cluster_personnel_tree.json"
    snapshot_path = config.SNAPSHOTS_DIR / "viettel_inventory_latest.json"

    if not tree_path.exists():
        print(f"❌ Không tìm thấy file {tree_path}!")
        return
    if not snapshot_path.exists():
        print(f"❌ Không tìm thấy file snapshot {snapshot_path}! Hãy chạy bước 03 trước.")
        return

    # 1. Load data
    personnel_stores = load_personnel_tree_stores(tree_path)
    crawled_stores, store_inventory = load_crawled_stores_and_inventory(snapshot_path)

    # 2. Match stores
    matched_results = match_stores(personnel_stores, crawled_stores)

    # 3. Save mapping JSON
    mapping_path = config.MASTER_DIR / "viettel_store_mapping.json"
    with open(mapping_path, "w", encoding="utf-8") as f:
        json.dump(matched_results, f, ensure_ascii=False, indent=2)
    print(f"✅ Đã lưu kết quả ánh xạ vào: {mapping_path}")

    # 4. Generate Interactive HTML Viewer
    output_html = config.REPORTS_DIR / "viettel_store_inventory_viewer.html"
    generate_viewer_html(matched_results, crawled_stores, store_inventory, output_html)
    print(f"🌐 Đã tạo giao diện tra cứu tồn kho trực quan: {output_html}")
    print("=" * 80)


if __name__ == "__main__":
    main()
