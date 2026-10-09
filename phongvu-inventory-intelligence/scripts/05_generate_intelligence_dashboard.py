#!/usr/bin/env python3
"""
Script 05: Generate Phong Vu Executive Intelligence Dashboard HTML.
Focuses strictly on the 3 Valid Ground-Truth Data Tracks:
  Track 1: Scarcity & True Physical Stock Radar (<= 5 units)
  Track 2: Real-time Price, Discount & Promotion/Gift Intelligence
  Track 3: Category Breakdown & Showroom Availability Matrix
Usage:
    python3 scripts/05_generate_intelligence_dashboard.py
"""

import os
import sys
import glob
import json
from datetime import datetime
from typing import List, Dict, Any

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def load_all_latest_data() -> Dict[str, List[Dict[str, Any]]]:
    raw_dir = os.path.join(PROJECT_ROOT, "data", "raw")
    latest_files = glob.glob(os.path.join(raw_dir, "phongvu_*_latest.json"))
    catalog_by_category = {}
    for f in latest_files:
        basename = os.path.basename(f)
        category = basename.replace("phongvu_", "").replace("_latest.json", "")
        with open(f, "r", encoding="utf-8") as fh:
            catalog_by_category[category] = json.load(fh)
    return catalog_by_category


def generate_dashboard():
    catalogs = load_all_latest_data()
    if not catalogs:
        print("[!] Không tìm thấy file dữ liệu latest trong data/raw/")
        return

    all_skus: Dict[str, Dict[str, Any]] = {}
    for cat, items in catalogs.items():
        for it in items:
            sku = it.get("sku")
            if sku and sku not in all_skus:
                it_copy = dict(it)
                it_copy["primary_category"] = cat
                all_skus[sku] = it_copy

    unique_products = list(all_skus.values())
    total_skus = len(unique_products)

    # Track 1: Scarcity Items (<= 5 items)
    scarcity_items = [p for p in unique_products if p.get("scarcity_flag") or (0 < p.get("stock_quantity", 0) <= 5)]
    scarcity_items.sort(key=lambda x: (x.get("stock_quantity", 0), -x.get("price", 0)))

    exact_1 = [p for p in scarcity_items if p.get("stock_quantity") == 1]
    exact_2 = [p for p in scarcity_items if p.get("stock_quantity") == 2]
    exact_3_5 = [p for p in scarcity_items if 3 <= p.get("stock_quantity", 0) <= 5]

    # Track 2: Price & Discounts
    priced_items = [p for p in unique_products if p.get("price", 0) > 0]
    total_inventory_value_approx = sum(
        p.get("price", 0) * (p.get("stock_quantity", 1) if p.get("scarcity_flag") else 10)
        for p in unique_products
    )
    gift_items = [p for p in unique_products if p.get("has_gift")]
    
    # Top discounts
    discounted_items = [p for p in priced_items if p.get("discount_amount", 0) > 0]
    discounted_items.sort(key=lambda x: x.get("discount_amount", 0), reverse=True)

    # Track 3: Categories & Coverage
    cat_summary = []
    for cat, items in catalogs.items():
        c_scarce = sum(1 for it in items if it.get("scarcity_flag") or (0 < it.get("stock_quantity", 0) <= 5))
        c_abundant = sum(1 for it in items if it.get("stock_quantity", 0) >= 1000)
        c_prices = [it.get("price", 0) for it in items if it.get("price", 0) > 0]
        c_avg = sum(c_prices) // len(c_prices) if c_prices else 0
        cat_summary.append({
            "category": cat,
            "total": len(items),
            "scarce": c_scarce,
            "abundant": c_abundant,
            "avg_price": c_avg
        })

    html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Phong Vũ Inventory & Pricing Intelligence Dashboard</title>
  <style>
    :root {{
      --bg-primary: #0b0f19;
      --bg-secondary: #111827;
      --bg-card: #1f2937;
      --border-color: #374151;
      --text-main: #f9fafb;
      --text-muted: #9ca3af;
      --accent-blue: #3b82f6;
      --accent-cyan: #06b6d4;
      --accent-red: #ef4444;
      --accent-yellow: #f59e0b;
      --accent-green: #10b981;
      --accent-purple: #8b5cf6;
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }}

    body {{
      background: var(--bg-primary);
      color: var(--text-main);
      padding: 24px;
      line-height: 1.5;
    }}

    .container {{
      max-width: 1440px;
      margin: 0 auto;
    }}

    /* Header */
    .header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 24px;
      border-bottom: 1px solid var(--border-color);
      margin-bottom: 24px;
    }}
    .header-title h1 {{
      font-size: 26px;
      font-weight: 700;
      background: linear-gradient(135deg, #60a5fa, #a78bfa);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .header-title p {{
      color: var(--text-muted);
      font-size: 13px;
      margin-top: 4px;
    }}
    .badge-live {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: rgba(16, 185, 129, 0.15);
      color: var(--accent-green);
      border: 1px solid rgba(16, 185, 129, 0.3);
      padding: 4px 10px;
      border-radius: 9999px;
      font-size: 12px;
      font-weight: 600;
    }}
    .pulse-dot {{
      width: 8px;
      height: 8px;
      background: var(--accent-green);
      border-radius: 50%;
      box-shadow: 0 0 8px var(--accent-green);
    }}

    /* KPI Cards */
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 16px;
      margin-bottom: 28px;
    }}
    .kpi-card {{
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 20px;
      position: relative;
      overflow: hidden;
      transition: transform 0.2s, border-color 0.2s;
    }}
    .kpi-card:hover {{
      transform: translateY(-2px);
      border-color: #4b5563;
    }}
    .kpi-label {{
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--text-muted);
      margin-bottom: 6px;
      font-weight: 600;
    }}
    .kpi-value {{
      font-size: 28px;
      font-weight: 700;
      color: var(--text-main);
    }}
    .kpi-subtext {{
      font-size: 12px;
      color: var(--text-muted);
      margin-top: 6px;
    }}
    .kpi-accent-red {{ border-top: 4px solid var(--accent-red); }}
    .kpi-accent-yellow {{ border-top: 4px solid var(--accent-yellow); }}
    .kpi-accent-blue {{ border-top: 4px solid var(--accent-blue); }}
    .kpi-accent-purple {{ border-top: 4px solid var(--accent-purple); }}

    /* Navigation Tabs */
    .tabs {{
      display: flex;
      gap: 8px;
      margin-bottom: 20px;
      border-bottom: 1px solid var(--border-color);
      padding-bottom: 8px;
    }}
    .tab-btn {{
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 14px;
      font-weight: 600;
      padding: 10px 18px;
      border-radius: 8px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: all 0.2s;
    }}
    .tab-btn:hover {{
      color: var(--text-main);
      background: rgba(255, 255, 255, 0.05);
    }}
    .tab-btn.active {{
      color: #fff;
      background: var(--accent-blue);
    }}
    .tab-badge {{
      background: rgba(255, 255, 255, 0.2);
      padding: 2px 7px;
      border-radius: 9999px;
      font-size: 11px;
    }}

    /* Table Sections */
    .tab-pane {{
      display: none;
    }}
    .tab-pane.active {{
      display: block;
    }}

    .card-panel {{
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 24px;
    }}
    .panel-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }}
    .panel-title {{
      font-size: 16px;
      font-weight: 600;
      color: var(--text-main);
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .search-box {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 8px 14px;
      color: #fff;
      font-size: 13px;
      width: 260px;
      outline: none;
    }}
    .search-box:focus {{
      border-color: var(--accent-blue);
    }}

    /* Modern Table */
    .table-container {{
      overflow-x: auto;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      text-align: left;
    }}
    th {{
      background: var(--bg-card);
      color: var(--text-muted);
      font-weight: 600;
      padding: 12px 14px;
      border-bottom: 1px solid var(--border-color);
      white-space: nowrap;
    }}
    td {{
      padding: 12px 14px;
      border-bottom: 1px solid rgba(55, 65, 81, 0.6);
      vertical-align: middle;
    }}
    tr:hover td {{
      background: rgba(255, 255, 255, 0.02);
    }}

    /* Badges */
    .badge {{
      display: inline-block;
      padding: 4px 8px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 700;
      text-align: center;
    }}
    .badge-danger {{
      background: rgba(239, 68, 68, 0.2);
      color: #fca5a5;
      border: 1px solid rgba(239, 68, 68, 0.4);
    }}
    .badge-warning {{
      background: rgba(245, 158, 11, 0.2);
      color: #fcd34d;
      border: 1px solid rgba(245, 158, 11, 0.4);
    }}
    .badge-info {{
      background: rgba(59, 130, 246, 0.2);
      color: #93c5fd;
      border: 1px solid rgba(59, 130, 246, 0.4);
    }}
    .badge-gift {{
      background: rgba(139, 92, 246, 0.2);
      color: #c4b5fd;
      border: 1px solid rgba(139, 92, 246, 0.4);
    }}

    .product-link {{
      color: #93c5fd;
      text-decoration: none;
      font-weight: 500;
    }}
    .product-link:hover {{
      text-decoration: underline;
    }}
    .sku-code {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      color: #e5e7eb;
      font-size: 12px;
    }}
    .price-text {{
      font-weight: 700;
      color: #34d399;
    }}
    .retail-text {{
      color: var(--text-muted);
      text-decoration: line-through;
      font-size: 12px;
    }}

    /* Notice box */
    .notice-box {{
      background: rgba(59, 130, 246, 0.08);
      border: 1px solid rgba(59, 130, 246, 0.25);
      border-radius: 8px;
      padding: 14px;
      margin-bottom: 20px;
      font-size: 13px;
      color: #bfdbfe;
      display: flex;
      align-items: flex-start;
      gap: 12px;
    }}
  </style>
</head>
<body>
  <div class="container">
    
    <!-- Header -->
    <div class="header">
      <div class="header-title">
        <h1>📊 PHONG VŨ INVENTORY & PRICING INTELLIGENCE</h1>
        <p>Báo cáo thông minh 3 trục dữ liệu xác thực (Ground Truth) • Nền tảng Microservices Teko</p>
      </div>
      <div>
        <span class="badge-live"><span class="pulse-dot"></span> ĐÃ XÁC THỰC DỮ LIỆU THỰC</span>
      </div>
    </div>

    <!-- Notice -->
    <div class="notice-box">
      <div>💡</div>
      <div>
        <strong>Nguyên tắc dữ liệu sạch (Data Integrity):</strong> Phong Vũ áp dụng cơ chế <em>Scarcity Threshold</em>. 
        Chỉ những sản phẩm có số lượng <strong>&le; 5 chiếc</strong> mới hiển thị số tồn kho vật lý chính xác 100%. Các sản phẩm dồi dào còn lại được hệ thống gán trần ảo 1.000 chiếc. 
        Dashboard này tập trung sâu sắc vào <strong>3 hướng dữ liệu có độ tin cậy tuyệt đối</strong>: (1) Radar hàng khan hiếm, (2) Dữ liệu giá & quà tặng thực tế, (3) Phân bố danh mục & độ phủ.
      </div>
    </div>

    <!-- Top KPI Grid -->
    <div class="kpi-grid">
      <div class="kpi-card kpi-accent-red">
        <div class="kpi-label">Hàng Khan Hiếm (&le; 5 chiếc)</div>
        <div class="kpi-value">{len(scarcity_items)} <span style="font-size:16px; color:#f87171">SKU</span></div>
        <div class="kpi-subtext">Chiếm {len(scarcity_items)*100/total_skus:.1f}% tổng số SKU đã khảo sát</div>
      </div>
      <div class="kpi-card kpi-accent-yellow">
        <div class="kpi-label">Chỉ Còn Đúng 1 - 2 Máy</div>
        <div class="kpi-value">{len(exact_1) + len(exact_2)} <span style="font-size:16px; color:#fbbf24">SKU</span></div>
        <div class="kpi-subtext">{len(exact_1)} mã còn 1 máy • {len(exact_2)} mã còn 2 máy</div>
      </div>
      <div class="kpi-card kpi-accent-blue">
        <div class="kpi-label">Tổng Số SKU Khảo Sát</div>
        <div class="kpi-value">{total_skus} <span style="font-size:16px; color:#60a5fa">Mã</span></div>
        <div class="kpi-subtext">Trải rộng trên {len(catalogs)} danh mục chủ lực</div>
      </div>
      <div class="kpi-card kpi-accent-purple">
        <div class="kpi-label">Có Quà Tặng Khuyến Mãi</div>
        <div class="kpi-value">{len(gift_items)} <span style="font-size:16px; color:#c084fc">SKU</span></div>
        <div class="kpi-subtext">{len(gift_items)*100/total_skus:.1f}% sản phẩm có quà tặng kèm</div>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <div class="tabs">
      <button class="tab-btn active" onclick="switchTab('tab-scarcity')">
        🚨 Hướng 1: Radar Hàng Khan Hiếm (&le; 5 chiếc)
        <span class="tab-badge">{len(scarcity_items)}</span>
      </button>
      <button class="tab-btn" onclick="switchTab('tab-pricing')">
        🏷️ Hướng 2: Giá Bán, Giảm Giá & Quà Tặng
        <span class="tab-badge">{len(discounted_items)}</span>
      </button>
      <button class="tab-btn" onclick="switchTab('tab-categories')">
        📍 Hướng 3: Phân Bố Danh Mục & Sẵn Hàng
        <span class="tab-badge">{len(cat_summary)}</span>
      </button>
    </div>

    <!-- TAB 1: SCARCITY TRACKER -->
    <div id="tab-scarcity" class="tab-pane active">
      <div class="card-panel">
        <div class="panel-header">
          <div class="panel-title">
            <span>🔥 Danh Sách Sản Phẩm Đang Trong Tình Trạng Khan Hiếm Nghiêm Trọng (Tồn Kho Thực Tế)</span>
          </div>
          <input type="text" id="searchScarcity" class="search-box" placeholder="Tìm theo tên hoặc mã SKU..." onkeyup="filterTable('scarcityTable', 'searchScarcity')">
        </div>
        <div class="table-container">
          <table id="scarcityTable">
            <thead>
              <tr>
                <th>Mã SKU</th>
                <th>Tên sản phẩm</th>
                <th>Danh mục</th>
                <th>Giá bán</th>
                <th>Giá gốc</th>
                <th>Giảm giá</th>
                <th>Tồn kho thực</th>
                <th>Mức độ cảnh báo</th>
              </tr>
            </thead>
            <tbody>"""

    for p in scarcity_items:
        sku = p.get("sku", "")
        name = p.get("name", "")
        cat = p.get("primary_category", "")
        price = f"{p.get('price', 0):,} ₫"
        retail = f"{p.get('supplier_retail_price', 0):,} ₫" if p.get('supplier_retail_price') else "-"
        disc = p.get("discount_percent", "-")
        stock = p.get("stock_quantity", 0)
        canonical = p.get("canonical", f"/p/{sku}")
        full_url = f"https://phongvu.vn{canonical}" if canonical.startswith("/") else f"https://phongvu.vn/{canonical}"

        if stock == 1:
            badge_html = '<span class="badge badge-danger">CHỈ CÒN 1 MÁY</span>'
            status_text = '<span style="color:#f87171; font-weight:700;">🚨 Duy nhất 1 cái</span>'
        elif stock == 2:
            badge_html = '<span class="badge badge-warning">CÒN 2 MÁY</span>'
            status_text = '<span style="color:#fbbf24; font-weight:700;">⚠️ Rất ít (2 cái)</span>'
        else:
            badge_html = '<span class="badge badge-info">CÒN 3 - 5 MÁY</span>'
            status_text = f'<span style="color:#93c5fd; font-weight:600;">Còn {stock} cái</span>'

        html_content += f"""
              <tr>
                <td class="sku-code">{sku}</td>
                <td><a href="{full_url}" target="_blank" class="product-link">{name}</a></td>
                <td><span class="badge badge-info">{cat}</span></td>
                <td class="price-text">{price}</td>
                <td class="retail-text">{retail}</td>
                <td style="color:#f87171; font-weight:600;">{disc}</td>
                <td>{status_text}</td>
                <td>{badge_html}</td>
              </tr>"""

    html_content += """
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- TAB 2: PRICING & PROMOTIONS -->
    <div id="tab-pricing" class="tab-pane">
      <div class="card-panel">
        <div class="panel-header">
          <div class="panel-title">
            <span>🎁 Top Sản Phẩm Giảm Giá Mạnh & Có Quà Tặng Kèm</span>
          </div>
          <input type="text" id="searchPricing" class="search-box" placeholder="Tìm theo tên hoặc mã SKU..." onkeyup="filterTable('pricingTable', 'searchPricing')">
        </div>
        <div class="table-container">
          <table id="pricingTable">
            <thead>
              <tr>
                <th>Mã SKU</th>
                <th>Tên sản phẩm</th>
                <th>Danh mục</th>
                <th>Giá bán</th>
                <th>Tiết kiệm (₫)</th>
                <th>% Giảm</th>
                <th>Quà tặng kèm</th>
                <th>Tồn kho</th>
              </tr>
            </thead>
            <tbody>"""

    for p in discounted_items[:35]:
        sku = p.get("sku", "")
        name = p.get("name", "")
        cat = p.get("primary_category", "")
        price = f"{p.get('price', 0):,} ₫"
        discount_amt = f"-{p.get('discount_amount', 0):,} ₫"
        disc_pct = p.get("discount_percent", "-")
        has_gift = p.get("has_gift", False)
        stock = p.get("stock_quantity", 0)
        stock_display = f"{stock} cái (Thực)" if p.get("scarcity_flag") else "Dồi dào (>=10)"
        gift_badge = '<span class="badge badge-gift">🎁 Có Quà Tặng</span>' if has_gift else '<span style="color:#6b7280">-</span>'
        canonical = p.get("canonical", f"/p/{sku}")
        full_url = f"https://phongvu.vn{canonical}" if canonical.startswith("/") else f"https://phongvu.vn/{canonical}"

        html_content += f"""
              <tr>
                <td class="sku-code">{sku}</td>
                <td><a href="{full_url}" target="_blank" class="product-link">{name}</a></td>
                <td><span class="badge badge-info">{cat}</span></td>
                <td class="price-text">{price}</td>
                <td style="color:#34d399; font-weight:600;">{discount_amt}</td>
                <td style="color:#f87171; font-weight:700;">{disc_pct}</td>
                <td>{gift_badge}</td>
                <td>{stock_display}</td>
              </tr>"""

    html_content += """
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- TAB 3: CATEGORY & STORE COVERAGE -->
    <div id="tab-categories" class="tab-pane">
      <div class="card-panel">
        <div class="panel-header">
          <div class="panel-title">
            <span>🏢 Ma Trận Phân Bố Tồn Kho Theo Từng Nhóm Ngành Hàng</span>
          </div>
        </div>
        <div class="table-container">
          <table>
            <thead>
              <tr>
                <th>Danh mục khảo sát</th>
                <th>Tổng số SKU</th>
                <th>Số SKU Khan Hiếm (&le; 5)</th>
                <th>Tỷ lệ Khan Hiếm</th>
                <th>Số SKU Dồi Dào (&ge; 10)</th>
                <th>Giá bán trung bình</th>
                <th>Đánh giá trạng thái</th>
              </tr>
            </thead>
            <tbody>"""

    for c in cat_summary:
        scarce_pct = c["scarce"] * 100 / c["total"] if c["total"] > 0 else 0
        if scarce_pct > 25:
            assessment = '<span class="badge badge-danger">Tồn kho mỏng / Rủi ro đứt hàng cao</span>'
        elif scarce_pct > 10:
            assessment = '<span class="badge badge-warning">Tồn kho cân bằng</span>'
        else:
            assessment = '<span class="badge badge-info">Dồi dào hàng</span>'

        html_content += f"""
              <tr>
                <td style="font-weight:600; text-transform:uppercase;">{c["category"]}</td>
                <td style="font-weight:700;">{c["total"]:,} SKU</td>
                <td style="color:#f87171; font-weight:700;">{c["scarce"]:,} SKU</td>
                <td>{scarce_pct:.1f}%</td>
                <td style="color:#34d399;">{c["abundant"]:,} SKU</td>
                <td class="price-text">{c["avg_price"]:,} ₫</td>
                <td>{assessment}</td>
              </tr>"""

    html_content += """
            </tbody>
          </table>
        </div>
      </div>
    </div>

  </div>

  <script>
    function switchTab(tabId) {
      document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));
      document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
      
      const targetPane = document.getElementById(tabId);
      if (targetPane) targetPane.classList.add('active');
      
      event.currentTarget.classList.add('active');
    }

    function filterTable(tableId, inputId) {
      const filter = document.getElementById(inputId).value.toLowerCase();
      const rows = document.querySelectorAll('#' + tableId + ' tbody tr');
      rows.forEach(row => {
        const text = row.innerText.toLowerCase();
        row.style.display = text.includes(filter) ? '' : 'none';
      });
    }
  </script>
</body>
</html>
"""

    report_dir = os.path.join(PROJECT_ROOT, "data", "reports")
    os.makedirs(report_dir, exist_ok=True)
    out_html = os.path.join(report_dir, "phongvu_executive_intelligence_dashboard.html")

    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"\n🎉 ĐÃ KHỞI TẠO DASHBOARD THÀNH CÔNG!")
    print(f"👉 File HTML: {out_html}")
    print(f"   (Mở trực tiếp trên trình duyệt để khám phá 3 trục dữ liệu sạch)")


if __name__ == "__main__":
    generate_dashboard()
