"""
FPT Store Inventory Intelligence - Dedicated Store Viewer Generator
===================================================================
Tạo file HTML độc lập phục vụ tra cứu tồn kho chi tiết theo Apple Store ID (store_code)
hoặc mã siêu thị FPT Shop (shopCode).

Đặc tính nâng cao:
1. Hiển thị SỐ LƯỢNG TỒN KHO THỰC TẾ (Actual On-Hand Units) của từng sản phẩm tại quầy.
2. Phân loại mức tồn: Cảnh báo hàng khan hiếm (Còn 1 máy) vs Sẵn hàng dồi dào (≥ 2 máy).
3. Khử trùng lặp kênh (De-duplication): Gom FPT Shop & F.Studio thành 1 dòng sản phẩm duy nhất.
4. Hỗ trợ Deep Linking URL Hash: open "viewer.html#store=3815062" hoặc "#3815062".
5. Tích hợp dữ liệu Cây Nhân Sự Apple: Quản lý, Chuyên viên Apple, Quy mô diện tích & Phân hạng doanh thu.
6. Live Autocomplete Search theo Apple ID / Tên đường / Mã Shop.
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, Any, List

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import MASTER_DIR, RAW_DATA_DIR, REPORTS_DIR, MASTER_STORES_FILE


def generate_store_viewer_html(output_file: str = None) -> str:
    if not output_file:
        output_file = os.path.join(REPORTS_DIR, "fpt_store_inventory_viewer.html")

    deep_json_file = os.path.join(RAW_DATA_DIR, "fpt_inventory_deep_latest.json")
    fast_json_file = os.path.join(RAW_DATA_DIR, "fpt_inventory_fast_latest.json")
    mapping_file = os.path.join(MASTER_DIR, "store_code_mapping.json")
    quantities_file = os.path.join(RAW_DATA_DIR, "store_inventory_quantities.json")

    catalog_file = None
    if os.path.exists(deep_json_file):
        catalog_file = deep_json_file
    elif os.path.exists(fast_json_file):
        catalog_file = fast_json_file

    if not os.path.exists(MASTER_STORES_FILE) or not catalog_file:
        print("⚠️ Chưa đủ file dữ liệu (cần master stores và ít nhất 1 snapshot fast/deep) để tạo Store Inventory Viewer.")
        return ""

    with open(MASTER_STORES_FILE, "r", encoding="utf-8") as f:
        master_stores = json.load(f)
    with open(catalog_file, "r", encoding="utf-8") as f:
        products = json.load(f)

    # Đọc mapping file nếu có để bổ sung các Apple ID đa xạ
    store_code_map = {}
    if os.path.exists(mapping_file):
        with open(mapping_file, "r", encoding="utf-8") as f:
            store_code_map = json.load(f)

    # Đọc dữ liệu số lượng tồn kho đã probe
    probed_quantities = {}
    if os.path.exists(quantities_file):
        try:
            with open(quantities_file, "r", encoding="utf-8") as f:
                probed_quantities = json.load(f)
        except Exception:
            probed_quantities = {}

    # Lập chỉ mục tồn kho theo từng shopCode (Đã khử trùng lặp kênh FPT Shop & F.Studio)
    # store_inventory[shopCode] = [ {sku_code, sku_name, category, price, channel, url, quantity, is_exact_qty}, ... ]
    store_inventory = {}
    for p in products:
        sku = p.get("sku_code")
        name = p.get("sku_name")
        cat = p.get("category")
        price = p.get("price")
        url = p.get("url")

        fpt_shops = {str(s.get("shopCode")) for s in p.get("fpt_store_list", []) if s.get("shopCode")}
        fstudio_shops = {str(s.get("shopCode")) for s in p.get("fstudio_store_list", []) if s.get("shopCode")}
        all_shops = fpt_shops | fstudio_shops

        for sc in all_shops:
            if sc not in store_inventory:
                store_inventory[sc] = []

            # Xác định kênh cung ứng
            if sc in fpt_shops and sc in fstudio_shops:
                channel = "FPT Shop & F.Studio"
            elif sc in fstudio_shops:
                channel = "F.Studio by FPT"
            else:
                channel = "FPT Shop"

            # Xác định số lượng tồn kho thực tế
            qty = 1
            is_exact = False
            if sc in probed_quantities:
                probed_items = probed_quantities[sc].get("items", {})
                if sku in probed_items:
                    qty = probed_items[sku]
                    is_exact = True

            store_inventory[sc].append({
                "sku_code": sku,
                "sku_name": name,
                "category": cat,
                "price": price,
                "channel": channel,
                "url": url,
                "quantity": qty,
                "is_exact_qty": is_exact
            })

    # Ưu tiên tuyệt đối item_details từ on-demand prober nếu có
    for sc, p_info in probed_quantities.items():
        sc = str(sc)
        if "item_details" in p_info and p_info["item_details"]:
            store_inventory[sc] = p_info["item_details"]
        elif sc in store_inventory and "items" in p_info:
            for it in store_inventory[sc]:
                sku = it["sku_code"]
                if sku in p_info["items"]:
                    it["quantity"] = p_info["items"][sku]
                    it["is_exact_qty"] = True

    # Đóng gói JSON nhúng vào HTML
    stores_json_str = json.dumps(master_stores, ensure_ascii=False)
    inventory_json_str = json.dumps(store_inventory, ensure_ascii=False)
    mapping_json_str = json.dumps(store_code_map, ensure_ascii=False)
    probed_json_str = json.dumps(probed_quantities, ensure_ascii=False)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>FPT Store Inventory Intelligence - Tra Cứu Tồn Kho Thực Tế Theo Apple Store ID</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-primary: #0a0e17;
      --bg-secondary: #121826;
      --card-bg: rgba(22, 29, 47, 0.78);
      --card-border: rgba(255, 255, 255, 0.08);
      --accent-fpt: #cb1c22;
      --accent-fstudio: #2997ff;
      --accent-amber: #f59e0b;
      --accent-green: #10b981;
      --accent-purple: #8b5cf6;
      --text-main: #f3f4f6;
      --text-muted: #9ca3af;
      --glass-blur: blur(18px);
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
        radial-gradient(at 0% 0%, rgba(203, 28, 34, 0.12) 0px, transparent 50%),
        radial-gradient(at 100% 0%, rgba(41, 151, 255, 0.12) 0px, transparent 50%),
        radial-gradient(at 50% 100%, rgba(139, 92, 246, 0.08) 0px, transparent 60%);
      background-attachment: fixed;
    }}

    .container {{
      max-width: 1440px;
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

    .badge-fpt {{
      background: linear-gradient(135deg, #cb1c22, #ea3a3d);
      color: white;
      font-weight: 800;
      font-size: 13px;
      padding: 6px 14px;
      border-radius: 8px;
      letter-spacing: 0.5px;
    }}

    .badge-apple {{
      background: rgba(41, 151, 255, 0.18);
      border: 1px solid rgba(41, 151, 255, 0.4);
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

    /* Quick Preset Chips */
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
      background: rgba(56, 189, 248, 0.2);
      border-color: #38bdf8;
      color: #38bdf8;
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
      grid-template-columns: 2.2fr 1fr 2fr auto;
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
      background: rgba(13, 19, 33, 0.9);
      border: 1px solid var(--card-border);
      color: var(--text-main);
      padding: 12px 16px;
      border-radius: 10px;
      font-size: 14px;
      outline: none;
      transition: border-color 0.2s, box-shadow 0.2s;
    }}

    .search-input:focus, .select-box:focus {{
      border-color: #38bdf8;
      box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.15);
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
      padding: 12px 16px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
      cursor: pointer;
      display: flex;
      justify-content: space-between;
      align-items: center;
      transition: background 0.15s;
    }}

    .autocomplete-item:hover {{
      background: rgba(56, 189, 248, 0.12);
    }}

    .btn-search {{
      background: linear-gradient(135deg, #2563eb, #1d4ed8);
      color: white;
      border: none;
      padding: 12px 24px;
      border-radius: 10px;
      font-weight: 700;
      font-size: 14px;
      cursor: pointer;
      transition: opacity 0.2s;
      white-space: nowrap;
    }}

    .btn-search:hover {{
      opacity: 0.9;
    }}

    /* Store Info Card */
    .store-hero {{
      background: var(--card-bg);
      backdrop-filter: var(--glass-blur);
      border: 1px solid var(--card-border);
      border-radius: 20px;
      padding: 28px;
      margin-bottom: 24px;
      display: grid;
      grid-template-columns: 1.8fr 1.2fr;
      gap: 28px;
    }}

    .store-title-area {{
      display: flex;
      flex-direction: column;
      gap: 12px;
    }}

    .store-name-lg {{
      font-size: 26px;
      font-weight: 800;
      letter-spacing: -0.5px;
      color: #ffffff;
      line-height: 1.3;
    }}

    .tag-container {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      align-items: center;
    }}

    .tag-tree {{
      background: rgba(245, 158, 11, 0.15);
      border: 1px solid rgba(245, 158, 11, 0.35);
      color: #fbbf24;
      font-size: 12px;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: 6px;
    }}

    .tag-shop {{
      background: rgba(56, 189, 248, 0.15);
      border: 1px solid rgba(56, 189, 248, 0.35);
      color: #38bdf8;
      font-size: 12px;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: 6px;
    }}

    .tag-cluster {{
      background: rgba(139, 92, 246, 0.15);
      border: 1px solid rgba(139, 92, 246, 0.35);
      color: #c084fc;
      font-size: 12px;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: 6px;
    }}

    .store-meta-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
      font-size: 13px;
      margin-top: 6px;
    }}

    .meta-item {{
      display: flex;
      flex-direction: column;
      gap: 4px;
    }}

    .meta-label {{
      color: var(--text-muted);
      font-size: 12px;
    }}

    .meta-val {{
      font-weight: 600;
      color: var(--text-main);
      line-height: 1.4;
    }}

    /* Quick Summary Box */
    .hero-summary-box {{
      background: rgba(15, 23, 42, 0.7);
      border-radius: 16px;
      padding: 22px;
      border: 1px solid var(--card-border);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 16px;
    }}

    .personnel-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      background: rgba(0, 0, 0, 0.2);
      border-radius: 10px;
      padding: 12px;
      font-size: 12px;
    }}

    .personnel-item {{
      display: flex;
      flex-direction: column;
      gap: 2px;
    }}

    /* KPI Summary Row */
    .kpi-row {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 16px;
      margin-bottom: 24px;
    }}

    .kpi-box {{
      background: var(--card-bg);
      backdrop-filter: var(--glass-blur);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 20px;
      text-align: center;
      transition: transform 0.2s;
    }}

    .kpi-box:hover {{
      transform: translateY(-2px);
    }}

    .kpi-num {{
      font-size: 28px;
      font-weight: 800;
      margin-top: 6px;
      letter-spacing: -0.5px;
    }}

    .kpi-subtext {{
      font-size: 12px;
      color: var(--text-muted);
      font-weight: 700;
      letter-spacing: 0.5px;
    }}

    /* Table Section */
    .table-card {{
      background: var(--card-bg);
      backdrop-filter: var(--glass-blur);
      border: 1px solid var(--card-border);
      border-radius: 18px;
      overflow: hidden;
      margin-bottom: 40px;
    }}

    .table-toolbar {{
      padding: 18px 24px;
      border-bottom: 1px solid var(--card-border);
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      flex-wrap: wrap;
    }}

    .table-filter-pills {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }}

    .pill-btn {{
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--card-border);
      color: var(--text-muted);
      padding: 6px 16px;
      border-radius: 20px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}

    .pill-btn.active, .pill-btn:hover {{
      background: rgba(56, 189, 248, 0.2);
      border-color: #38bdf8;
      color: #38bdf8;
    }}

    .pill-count {{
      background: rgba(255, 255, 255, 0.12);
      padding: 1px 7px;
      border-radius: 10px;
      font-size: 11px;
    }}

    .pill-btn.active .pill-count {{
      background: rgba(56, 189, 248, 0.4);
      color: white;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 14px;
    }}

    th {{
      background: rgba(18, 24, 38, 0.95);
      padding: 14px 20px;
      color: var(--text-muted);
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      border-bottom: 1px solid var(--card-border);
      letter-spacing: 0.5px;
    }}

    td {{
      padding: 16px 20px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.04);
      vertical-align: middle;
    }}

    tr:hover td {{
      background: rgba(255, 255, 255, 0.02);
    }}

    /* Badges cho Số Lượng Tồn Thực Tế */
    .badge-qty-high {{
      background: rgba(16, 185, 129, 0.2);
      border: 1px solid rgba(16, 185, 129, 0.45);
      color: #34d399;
      font-weight: 800;
      font-size: 13px;
      padding: 5px 12px;
      border-radius: 8px;
      display: inline-flex;
      align-items: center;
      gap: 5px;
    }}

    .badge-qty-good {{
      background: rgba(56, 189, 248, 0.2);
      border: 1px solid rgba(56, 189, 248, 0.45);
      color: #38bdf8;
      font-weight: 800;
      font-size: 13px;
      padding: 5px 12px;
      border-radius: 8px;
      display: inline-flex;
      align-items: center;
      gap: 5px;
    }}

    .badge-qty-warning {{
      background: rgba(245, 158, 11, 0.2);
      border: 1px solid rgba(245, 158, 11, 0.45);
      color: #fbbf24;
      font-weight: 800;
      font-size: 13px;
      padding: 5px 12px;
      border-radius: 8px;
      display: inline-flex;
      align-items: center;
      gap: 5px;
    }}

    .badge-qty-normal {{
      background: rgba(148, 163, 184, 0.15);
      border: 1px solid rgba(148, 163, 184, 0.35);
      color: #cbd5e1;
      font-weight: 700;
      font-size: 13px;
      padding: 5px 12px;
      border-radius: 8px;
      display: inline-flex;
      align-items: center;
      gap: 5px;
    }}

    .badge-in-stock {{
      background: rgba(16, 185, 129, 0.15);
      color: #34d399;
      border: 1px solid rgba(16, 185, 129, 0.35);
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 700;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}

    .badge-stock-warning {{
      background: rgba(245, 158, 11, 0.15);
      color: #fbbf24;
      border: 1px solid rgba(245, 158, 11, 0.35);
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 700;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}

    /* Badges cho Kênh Cung Ứng */
    .badge-channel-combo {{
      background: linear-gradient(135deg, rgba(203, 28, 34, 0.25), rgba(41, 151, 255, 0.25));
      border: 1px solid rgba(139, 92, 246, 0.4);
      color: #e0e7ff;
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 700;
      display: inline-block;
    }}

    .badge-channel-studio {{
      background: rgba(41, 151, 255, 0.2);
      border: 1px solid rgba(41, 151, 255, 0.35);
      color: #38bdf8;
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 700;
      display: inline-block;
    }}

    .badge-channel-fpt {{
      background: rgba(203, 28, 34, 0.2);
      border: 1px solid rgba(203, 28, 34, 0.35);
      color: #f87171;
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 700;
      display: inline-block;
    }}

    .btn-copy {{
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid var(--card-border);
      color: var(--text-muted);
      cursor: pointer;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 11px;
      margin-left: 6px;
      transition: all 0.2s;
    }}

    .btn-copy:hover {{
      background: rgba(56, 189, 248, 0.2);
      color: #38bdf8;
    }}

    .link-maps {{
      color: #38bdf8;
      text-decoration: none;
      font-weight: 600;
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }}

    .link-maps:hover {{
      text-decoration: underline;
    }}

    .toast {{
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: #10b981;
      color: white;
      padding: 10px 20px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 600;
      box-shadow: 0 10px 25px rgba(0,0,0,0.4);
      opacity: 0;
      transition: opacity 0.3s;
      pointer-events: none;
      z-index: 9999;
    }}
  </style>
</head>
<body>
  <div class="container">
    <!-- Header -->
    <header>
      <div class="brand-title">
        <span class="badge-fpt">FPT RETAIL</span>
        <span class="badge-apple">APPLE STORE INTELLIGENCE</span>
        <h1>Store-Level Inventory Viewer</h1>
      </div>
      <div style="font-size: 13px; color: var(--text-muted);">
        Dữ liệu Snapshot: <strong>{now_str}</strong>
      </div>
    </header>

    <!-- Probed Stores Dynamic Bar (Auto-generated from store_inventory_quantities.json) -->
    <div class="preset-bar" id="probedStoresBar" style="display: none; background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(52, 211, 153, 0.25); border-radius: 12px; padding: 10px 14px; margin-bottom: 14px;">
      <span class="preset-label" style="color: #34d399; display: flex; align-items: center; gap: 6px;">
        <span style="display: inline-block; width: 8px; height: 8px; background: #10b981; border-radius: 50%; box-shadow: 0 0 8px #10b981;"></span>
        🎯 SIÊU THỊ ĐÃ XÁC MINH SỐ LƯỢNG THỰC TẾ:
      </span>
      <div id="probedChipsContainer" style="display: flex; gap: 8px; flex-wrap: wrap;"></div>
    </div>

    <!-- Preset Shortcuts -->
    <div class="preset-bar">
      <span class="preset-label">⚡ Cửa Hàng Tiêu Biểu:</span>
      <button class="preset-chip" onclick="quickJump('3815062')">🍎 3815062 - F.Studio Buôn Ma Thuột (Đắk Lắk)</button>
      <button class="preset-chip" onclick="quickJump('3958531')">🍎 3958531 - F.Studio 121 Hai Bà Trưng (HCM)</button>
      <button class="preset-chip" onclick="quickJump('1659583')">🍎 1659583 - F.Studio 269 Chùa Bộc (Hà Nội)</button>
      <button class="preset-chip" onclick="quickJump('1472335')">🏬 1472335 - FPT Hòa Lạc (Thạch Thất)</button>
      <button class="preset-chip" onclick="quickJump('3744640')">🏬 3744640 - FPT 376A Nguyễn Thị Thập (Q.7)</button>
    </div>

    <!-- Control Panel -->
    <div class="control-panel">
      <!-- Search Input with Autocomplete -->
      <div class="search-wrapper">
        <input type="text" id="storeSearchInput" class="search-input" placeholder="🔍 Gõ Apple ID (VD: 3815062, 3958531), mã shop (30501), tên đường..." autocomplete="off">
        <div id="autocompleteList" class="autocomplete-list"></div>
      </div>

      <!-- Cluster Filter -->
      <div>
        <select id="clusterSelect" class="select-box">
          <option value="all">Tất cả Nhóm Cụm</option>
          <option value="A">Cụm Nhóm A</option>
          <option value="B">Cụm Nhóm B</option>
          <option value="C">Cụm Nhóm C</option>
          <option value="D">Cụm Nhóm D</option>
        </select>
      </div>

      <!-- Store Select Dropdown -->
      <div>
        <select id="storeDropdown" class="select-box"></select>
      </div>

      <!-- Action Button -->
      <div>
        <button class="btn-search" onclick="applySearch()">Xem Tồn Kho</button>
      </div>
    </div>

    <!-- Store Hero Header Card -->
    <div class="store-hero" id="storeHero">
      <div class="store-title-area">
        <div class="tag-container">
          <span class="tag-tree" id="lblTreeCode">Apple Tree ID: 3815062</span>
          <span class="tag-shop" id="lblShopCode">Mã FPT PAPI: 30501</span>
          <span class="tag-cluster" id="lblCluster">Nhóm A</span>
          <span class="tag-tree" id="lblChannelBadge" style="background: rgba(41, 151, 255, 0.15); border-color: rgba(41, 151, 255, 0.35); color: #38bdf8;">F.Studio</span>
          <span class="tag-tree" id="lblProbeBadge" style="display: none; background: rgba(16, 185, 129, 0.2); border-color: rgba(52, 211, 153, 0.5); color: #34d399; font-weight: 700;">🎯 ĐÃ XÁC MINH SỐ LƯỢNG THỰC TẾ</span>
        </div>
        <div class="store-name-lg" id="lblStoreName">DLK 37 Lê Thánh Tông</div>
        <div style="font-size: 14px; color: var(--text-muted);" id="lblTreeName">F-Studio By Fpt @ 37 Le Thanh Tong</div>
        
        <div class="store-meta-grid">
          <div class="meta-item">
            <span class="meta-label">📍 Địa chỉ chuẩn hóa:</span>
            <span class="meta-val" id="lblAddress">37 Lê Thánh Tông, P. Buôn Ma Thuột, Tỉnh Đắk Lắk</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">🔄 Địa chỉ trước sáp nhập:</span>
            <span class="meta-val" id="lblLegacyAddress">Số 37 Lê Thánh Tông, P Thắng Lợi, TP Buôn Ma Thuột</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">🌐 Tọa độ định vị GPS:</span>
            <span class="meta-val">
              <a href="#" target="_blank" class="link-maps" id="linkGps">12.683552, 108.047191 ↗</a>
            </span>
          </div>
          <div class="meta-item">
            <span class="meta-label">⏰ Giờ hoạt động & Hotline:</span>
            <span class="meta-val" id="lblOpenTime">07:30 - 22:00 | 1800 6601</span>
          </div>
        </div>
      </div>

      <!-- Quick Summary Box -->
      <div class="hero-summary-box">
        <div>
          <div style="font-size: 13px; color: var(--text-muted); font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">SỨC KHỎE TỒN KHO TẠI QUẦY:</div>
          <div style="font-size: 32px; font-weight: 800; color: #34d399; margin: 6px 0;" id="lblTotalSkusHero">11 BIẾN THỂ (15 MÁY)</div>
          <div style="font-size: 13px; color: var(--text-muted); line-height: 1.4;">
            Toàn bộ các mặt hàng hiển thị dưới đây đều <strong>có sẵn máy vật lý tại quầy</strong> để khách hàng ghé lấy ngay.
          </div>
        </div>

        <!-- Personnel & Management Info -->
        <div class="personnel-grid" id="personnelBox">
          <div class="personnel-item">
            <span style="color: var(--text-muted);">👤 Quản lý Cửa Hàng:</span>
            <strong id="lblManager" style="color: #fbbf24;">Đang cập nhật</strong>
          </div>
          <div class="personnel-item">
            <span style="color: var(--text-muted);">⭐ Apple Expert:</span>
            <strong id="lblExpert" style="color: #38bdf8;">Đang cập nhật</strong>
          </div>
          <div class="personnel-item">
            <span style="color: var(--text-muted);">📐 Quy mô diện tích:</span>
            <strong id="lblStoreSize">Tiêu chuẩn</strong>
          </div>
          <div class="personnel-item">
            <span style="color: var(--text-muted);">💼 Phân hạng Doanh thu:</span>
            <strong id="lblRevenue">Hạng A</strong>
          </div>
        </div>
      </div>
    </div>

    <!-- KPI Row -->
    <div class="kpi-row">
      <div class="kpi-box">
        <div class="kpi-subtext">BIẾN THỂ SẴN HÀNG</div>
        <div class="kpi-num" style="color: #34d399;" id="kpiSkus">11</div>
      </div>
      <div class="kpi-box">
        <div class="kpi-subtext">SỐ MÁY VẬT LÝ TẠI QUẦY</div>
        <div class="kpi-num" style="color: #38bdf8;" id="kpiUnits">15 máy</div>
      </div>
      <div class="kpi-box">
        <div class="kpi-subtext">TỔNG GIÁ TRỊ TỒN TRƯNG BÀY</div>
        <div class="kpi-num" style="color: #fbbf24;" id="kpiValue">~450 Tr đ</div>
      </div>
      <div class="kpi-box">
        <div class="kpi-subtext">TỶ LỆ PHỦ DANH MỤC APPLE</div>
        <div class="kpi-num" style="color: #c084fc;" id="kpiRate">2.3%</div>
      </div>
    </div>

    <!-- Table Section -->
    <div class="table-card">
      <div class="table-toolbar">
        <div class="table-filter-pills" id="categoryPills">
          <button class="pill-btn active" data-cat="all">Tất Cả <span class="pill-count" id="countAll">0</span></button>
          <button class="pill-btn" data-cat="iPhone">iPhone <span class="pill-count" id="countIphone">0</span></button>
          <button class="pill-btn" data-cat="iPad">iPad <span class="pill-count" id="countIpad">0</span></button>
          <button class="pill-btn" data-cat="MacBook">MacBook <span class="pill-count" id="countMac">0</span></button>
          <button class="pill-btn" data-cat="Apple Watch">Apple Watch <span class="pill-count" id="countWatch">0</span></button>
          <button class="pill-btn" data-cat="AirPods">AirPods <span class="pill-count" id="countAirpods">0</span></button>
        </div>
        <div>
          <input type="text" id="productFilterInput" class="search-input" style="padding: 8px 14px; font-size: 13px; min-width: 260px;" placeholder="🔍 Lọc nhanh theo tên SKU, màu, GB...">
        </div>
      </div>

      <table>
        <thead>
          <tr>
            <th>Ngành Hàng</th>
            <th>Mã SKU</th>
            <th>Tên Sản Phẩm / Biến Thể</th>
            <th>Kênh Cung Ứng</th>
            <th>Giá Niêm Yết</th>
            <th>Tồn Kho Tại Quầy</th>
            <th>Tình Trạng</th>
            <th>Thao Tác</th>
          </tr>
        </thead>
        <tbody id="inventoryTableBody"></tbody>
      </table>
    </div>
  </div>

  <div id="toast" class="toast">Đã sao chép SKU vào clipboard!</div>

  <script>
    const storesData = {stores_json_str};
    const inventoryData = {inventory_json_str};
    const codeMapping = {mapping_json_str};
    const probedData = {probed_json_str};

    let currentShopCode = "30501"; // Mặc định mở 30501 (3815062)
    let currentCategory = "all";
    let productSearchText = "";

    function showToast(msg) {{
      const t = document.getElementById("toast");
      t.innerText = msg;
      t.style.opacity = "1";
      setTimeout(() => {{ t.style.opacity = "0"; }}, 2000);
    }}

    function copySku(sku) {{
      navigator.clipboard.writeText(sku).then(() => {{
        showToast("Đã sao chép mã SKU: " + sku);
      }});
    }}

    // Khởi tạo dropdown danh sách cửa hàng
    function initDropdown() {{
      const select = document.getElementById("storeDropdown");
      select.innerHTML = "";
      
      const clusterFilter = document.getElementById("clusterSelect").value;

      storesData.forEach(s => {{
        if (clusterFilter !== "all" && s.cluster_group !== clusterFilter) return;

        const opt = document.createElement("option");
        opt.value = s.shopCode;
        const treeInfo = s.store_code ? `[Apple: ${{s.store_code}}] ` : "";
        const clusterInfo = s.cluster_group ? `(Cụm ${{s.cluster_group}}) ` : "";
        const addrShort = (s.displayAddress || "").slice(0, 32);
        const isProbed = Boolean(probedData[s.shopCode]);
        const probeTag = isProbed ? `🎯 [XÁC MINH: ${{probedData[s.shopCode].total_units}} MÁY] ` : "";
        opt.text = `${{probeTag}}${{treeInfo}}${{s.shopName}} ${{clusterInfo}}- ${{addrShort}}...`;
        if (String(s.shopCode) === currentShopCode) opt.selected = true;
        select.appendChild(opt);
      }});
    }}

    function renderProbedPresets() {{
      const bar = document.getElementById("probedStoresBar");
      const container = document.getElementById("probedChipsContainer");
      if (!bar || !container) return;
      const probedKeys = Object.keys(probedData);
      if (probedKeys.length === 0) {{
        bar.style.display = "none";
        return;
      }}
      bar.style.display = "flex";
      container.innerHTML = "";
      probedKeys.forEach(sc => {{
        const p = probedData[sc];
        const s = storesData.find(st => String(st.shopCode) === sc);
        const storeLabel = s ? (s.store_code ? `${{s.store_code}} - ${{s.shopName}}` : `${{sc}} - ${{s.shopName}}`) : (p.shop_name || sc);
        const btn = document.createElement("button");
        btn.className = "preset-chip";
        btn.style.borderColor = "rgba(52, 211, 153, 0.45)";
        btn.style.color = "#34d399";
        btn.style.background = "rgba(16, 185, 129, 0.12)";
        btn.innerHTML = `🎯 <strong>${{storeLabel}}</strong> (${{p.total_units}} máy)`;
        btn.onclick = () => quickJump(sc);
        container.appendChild(btn);
      }});
    }}

    // Tìm kiếm cửa hàng từ Apple ID hoặc query
    function findStoreByAnyCode(query) {{
      const q = String(query).trim().toLowerCase();
      if (!q) return null;

      // 1. Kiểm tra trực tiếp trong mapping code
      if (codeMapping[q]) {{
        const targetSc = String(codeMapping[q].shopCode);
        const match = storesData.find(s => String(s.shopCode) === targetSc);
        if (match) return match;
      }}

      // 2. Kiểm tra trong master stores
      return storesData.find(s => {{
        const sc = String(s.shopCode || "").toLowerCase();
        const tc = String(s.store_code || "").toLowerCase();
        const name = String(s.shopName || "").toLowerCase();
        const tname = String(s.store_name || "").toLowerCase();
        const addr = String(s.displayAddress || "").toLowerCase();
        return sc === q || tc === q || name.includes(q) || tname.includes(q) || addr.includes(q);
      }});
    }}

    // Chuyển đổi hiển thị siêu thị
    function loadStore(shopCode) {{
      currentShopCode = String(shopCode);
      const store = storesData.find(s => String(s.shopCode) === currentShopCode);
      if (!store) return;

      // Cập nhật URL Hash để chia sẻ trực tiếp
      const targetHash = store.store_code ? `store=${{store.store_code}}` : `store=${{store.shopCode}}`;
      window.location.hash = targetHash;

      // Cập nhật thông tin Store Hero
      document.getElementById("lblTreeCode").innerText = store.store_code ? `Apple ID: ${{store.store_code}}` : `Mã Shop: ${{store.shopCode}}`;
      document.getElementById("lblShopCode").innerText = `Mã FPT PAPI: ${{store.shopCode}}`;
      document.getElementById("lblCluster").innerText = store.cluster_group ? `Cụm Nhóm ${{store.cluster_group}}` : "Độc Lập";
      document.getElementById("lblChannelBadge").innerText = store.channel || "FPT Shop";
      document.getElementById("lblStoreName").innerText = store.shopName;
      document.getElementById("lblTreeName").innerText = store.store_name || (store.channel + " - " + store.displayAddress);
      document.getElementById("lblAddress").innerText = store.displayAddress || "Đang cập nhật";
      document.getElementById("lblLegacyAddress").innerText = store.legacyAddress || "Không có thay đổi";
      document.getElementById("lblOpenTime").innerText = `${{store.timeOpen || '08:00'}} - ${{store.timeClose || '22:00'}} | Hotline: ${{store.phone || '1800 6601'}}`;

      // Cập nhật Probe Badge
      const probeBadge = document.getElementById("lblProbeBadge");
      const pInfo = probedData[currentShopCode];
      if (pInfo && pInfo.total_units !== undefined) {{
        probeBadge.style.display = "inline-flex";
        probeBadge.innerText = `🎯 ĐÃ XÁC MINH THỰC TẾ: ${{pInfo.total_units}} MÁY (${{pInfo.probed_at || ''}})`;
      }} else {{
        probeBadge.style.display = "none";
      }}

      if (store.latitude && store.longitude) {{
        const mapUrl = `https://www.google.com/maps?q=${{store.latitude}},${{store.longitude}}`;
        const link = document.getElementById("linkGps");
        link.href = mapUrl;
        link.innerText = `${{store.latitude}}, ${{store.longitude}} ↗`;
      }}

      // Cập nhật thông tin nhân sự & quy mô
      const managers = store.manager || [];
      const experts = store.expert || [];
      document.getElementById("lblManager").innerText = managers.length > 0 ? managers.map(m => m.name).filter(Boolean).join(", ") || "Quản lý FPT" : "Chưa gắn mã";
      document.getElementById("lblExpert").innerText = experts.length > 0 ? experts.map(e => e.name).filter(Boolean).join(", ") || "Apple Expert" : "Chưa gắn mã";
      document.getElementById("lblStoreSize").innerText = store.store_size ? `${{store.store_size}} m²` : "Tiêu chuẩn";
      document.getElementById("lblRevenue").innerText = store.revenue ? `Hạng ${{store.revenue}}` : "Hạng A";

      // Cập nhật danh sách tồn kho & tính toán KPI số lượng
      const items = inventoryData[currentShopCode] || [];
      let totalUnits = 0;
      let totalVal = 0;
      let hasExactProbe = false;
      let counts = {{ "iPhone": 0, "iPad": 0, "MacBook": 0, "Apple Watch": 0, "AirPods": 0 }};

      items.forEach(it => {{
        const itemQty = it.quantity || 1;
        totalUnits += itemQty;
        totalVal += (it.price || 0) * itemQty;
        if (it.is_exact_qty) hasExactProbe = true;
        if (counts[it.category] !== undefined) counts[it.category]++;
      }});

      document.getElementById("lblTotalSkusHero").innerText = `${{items.length}} BIẾN THỂ (${{totalUnits}} MÁY VẬT LÝ)`;
      document.getElementById("kpiSkus").innerText = items.length;
      document.getElementById("kpiUnits").innerText = hasExactProbe ? `${{totalUnits}} máy vật lý` : `${{totalUnits}}+ máy`;

      document.getElementById("countAll").innerText = items.length;
      document.getElementById("countIphone").innerText = counts["iPhone"] || 0;
      document.getElementById("countIpad").innerText = counts["iPad"] || 0;
      document.getElementById("countMac").innerText = counts["MacBook"] || 0;
      document.getElementById("countWatch").innerText = counts["Apple Watch"] || 0;
      document.getElementById("countAirpods").innerText = counts["AirPods"] || 0;

      document.getElementById("kpiValue").innerText = new Intl.NumberFormat('vi-VN', {{ style: 'currency', currency: 'VND' }}).format(totalVal);
      document.getElementById("kpiRate").innerText = `${{(items.length * 100 / 482).toFixed(1)}}%`;

      renderTable();
    }}

    // Render bảng sản phẩm
    function renderTable() {{
      const tbody = document.getElementById("inventoryTableBody");
      tbody.innerHTML = "";

      const items = inventoryData[currentShopCode] || [];
      const filtered = items.filter(it => {{
        const matchCat = (currentCategory === "all") || (it.category === currentCategory);
        const query = productSearchText.toLowerCase();
        const matchSearch = !query || it.sku_name.toLowerCase().includes(query) || it.sku_code.toLowerCase().includes(query);
        return matchCat && matchSearch;
      }});

      if (filtered.length === 0) {{
        tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; padding: 48px; color: var(--text-muted);">Hiện không có sản phẩm nào thuộc bộ lọc này có sẵn tại quầy.</td></tr>`;
        return;
      }}

      filtered.forEach(it => {{
        const tr = document.createElement("tr");
        const priceStr = new Intl.NumberFormat('vi-VN', {{ style: 'currency', currency: 'VND' }}).format(it.price);
        
        // Kênh cung ứng badge
        let channelBadge = "";
        if (it.channel === "FPT Shop & F.Studio") {{
          channelBadge = `<span class="badge-channel-combo">FPT Shop & F.Studio</span>`;
        }} else if (it.channel === "F.Studio by FPT") {{
          channelBadge = `<span class="badge-channel-studio">F.Studio by FPT</span>`;
        }} else {{
          channelBadge = `<span class="badge-channel-fpt">FPT Shop</span>`;
        }}

        // Badge số lượng tồn kho thực tế
        let qtyBadge = "";
        let statusBadge = "";
        const q = it.quantity || 1;

        if (it.is_exact_qty) {{
          if (q >= 3) {{
            qtyBadge = `<span class="badge-qty-high">✓ ${{q}} máy</span>`;
            statusBadge = `<span class="badge-in-stock">● Sẵn hàng dồi dào</span>`;
          }} else if (q === 2) {{
            qtyBadge = `<span class="badge-qty-good">✓ 2 máy</span>`;
            statusBadge = `<span class="badge-in-stock">● Sẵn hàng quầy</span>`;
          }} else {{
            qtyBadge = `<span class="badge-qty-warning">⚠️ 1 máy</span>`;
            statusBadge = `<span class="badge-stock-warning">● Cảnh báo còn 1 cây</span>`;
          }}
        }} else {{
          qtyBadge = `<span class="badge-qty-normal">● ≥ 1 máy</span>`;
          statusBadge = `<span class="badge-in-stock">● Sẵn hàng quầy</span>`;
        }}

        tr.innerHTML = `
          <td><strong>${{it.category}}</strong></td>
          <td>
            <code>${{it.sku_code}}</code>
            <button class="btn-copy" onclick="copySku('${{it.sku_code}}')" title="Sao chép SKU">📋 Copy</button>
          </td>
          <td><a href="${{it.url}}" target="_blank" style="color: #f3f4f6; text-decoration: none; font-weight: 600;">${{it.sku_name}}</a></td>
          <td>${{channelBadge}}</td>
          <td><strong>${{priceStr}}</strong></td>
          <td>${{qtyBadge}}</td>
          <td>${{statusBadge}}</td>
          <td><a href="${{it.url}}" target="_blank" style="color: #38bdf8; text-decoration: none; font-weight: 600; font-size: 13px;">Đặt Mua ↗</a></td>
        `;
        tbody.appendChild(tr);
      }});
    }}

    function applySearch() {{
      const query = document.getElementById("storeSearchInput").value.trim();
      if (!query) return;

      const found = findStoreByAnyCode(query);
      if (found) {{
        document.getElementById("storeDropdown").value = found.shopCode;
        loadStore(found.shopCode);
        closeAutocomplete();
      }} else {{
        alert("Không tìm thấy siêu thị nào khớp với từ khóa: " + query);
      }}
    }}

    function quickJump(code) {{
      const found = findStoreByAnyCode(code);
      if (found) {{
        document.getElementById("storeDropdown").value = found.shopCode;
        loadStore(found.shopCode);
      }}
    }}

    // Autocomplete live suggestion
    const searchInput = document.getElementById("storeSearchInput");
    const autoList = document.getElementById("autocompleteList");

    searchInput.addEventListener("input", (e) => {{
      const q = e.target.value.trim().toLowerCase();
      if (q.length < 2) {{
        closeAutocomplete();
        return;
      }}

      const matches = storesData.filter(s => {{
        const sc = String(s.shopCode || "").toLowerCase();
        const tc = String(s.store_code || "").toLowerCase();
        const name = String(s.shopName || "").toLowerCase();
        const addr = String(s.displayAddress || "").toLowerCase();
        return sc.includes(q) || tc.includes(q) || name.includes(q) || addr.includes(q);
      }}).slice(0, 10);

      if (matches.length === 0) {{
        closeAutocomplete();
        return;
      }}

      autoList.innerHTML = "";
      matches.forEach(m => {{
        const div = document.createElement("div");
        div.className = "autocomplete-item";
        const treeBadge = m.store_code ? `<span class="tag-tree">Apple: ${{m.store_code}}</span>` : "";
        div.innerHTML = `
          <div>
            <div style="font-weight: 700; color: #ffffff;">${{m.shopName}}</div>
            <div style="font-size: 12px; color: var(--text-muted);">${{m.displayAddress.slice(0, 50)}}...</div>
          </div>
          <div style="display: flex; gap: 6px; align-items: center;">
            ${{treeBadge}}
            <span class="tag-shop">${{m.shopCode}}</span>
          </div>
        `;
        div.onclick = () => {{
          searchInput.value = m.store_code || m.shopCode;
          document.getElementById("storeDropdown").value = m.shopCode;
          loadStore(m.shopCode);
          closeAutocomplete();
        }};
        autoList.appendChild(div);
      }});
      autoList.style.display = "block";
    }});

    function closeAutocomplete() {{
      autoList.style.display = "none";
    }}

    document.addEventListener("click", (e) => {{
      if (!e.target.closest(".search-wrapper")) closeAutocomplete();
    }});

    // Xử lý Hash trên URL (#store=3815062 hoặc #3815062)
    function handleUrlHash() {{
      let hash = window.location.hash.replace("#", "").trim();
      if (!hash) return;

      if (hash.startsWith("store=")) {{
        hash = hash.split("store=")[1].split("&")[0].trim();
      }}

      const found = findStoreByAnyCode(hash);
      if (found) {{
        currentShopCode = String(found.shopCode);
        document.getElementById("storeDropdown").value = currentShopCode;
      }}
    }}

    // Event listeners
    document.getElementById("storeDropdown").addEventListener("change", (e) => {{
      loadStore(e.target.value);
    }});

    document.getElementById("clusterSelect").addEventListener("change", () => {{
      initDropdown();
    }});

    searchInput.addEventListener("keypress", (e) => {{
      if (e.key === "Enter") applySearch();
    }});

    document.getElementById("productFilterInput").addEventListener("input", (e) => {{
      productSearchText = e.target.value.trim();
      renderTable();
    }});

    document.querySelectorAll("#categoryPills .pill-btn").forEach(btn => {{
      btn.addEventListener("click", () => {{
        document.querySelectorAll("#categoryPills .pill-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        currentCategory = btn.getAttribute("data-cat");
        renderTable();
      }});
    }});

    window.addEventListener("hashchange", () => {{
      handleUrlHash();
      loadStore(currentShopCode);
    }});

    // Khởi chạy
    renderProbedPresets();
    initDropdown();
    handleUrlHash();
    if (!window.location.hash) {{
      const probedKeys = Object.keys(probedData);
      if (probedKeys.length > 0) {{
        currentShopCode = probedKeys[probedKeys.length - 1];
        document.getElementById("storeDropdown").value = currentShopCode;
      }}
    }}
    loadStore(currentShopCode);
  </script>
</body>
</html>
"""

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"✨ Đã xuất Store Inventory Viewer HTML thành công: {output_file}")
    return output_file


if __name__ == "__main__":
    generate_store_viewer_html()
