"""
FPT Inventory Intelligence - Executive HTML Dashboard Generator
=================================================================
Tạo trang Dashboard HTML tương tác cao cấp (Apple Glassmorphism UI):
- KPI Cards động hiển thị Ground-Truth Metrics.
- Bộ lọc theo ngành hàng (iPhone, iPad, Mac, Watch, AirPods) & trạng thái tồn kho.
- Bảng danh mục sản phẩm có thanh tìm kiếm thời gian thực.
- Modal xem chi tiết danh sách siêu thị FPT Shop & F.Studio có sẵn máy tại quầy.
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, Any, List

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import RAW_DATA_DIR, PREDICTIONS_DIR, REPORTS_DIR


def generate_html_dashboard(raw_json_path: str = None, inference_json_path: str = None) -> str:
    if not raw_json_path:
        raw_json_path = os.path.join(RAW_DATA_DIR, "fpt_inventory_deep_latest.json")
    if not inference_json_path:
        inference_json_path = os.path.join(PREDICTIONS_DIR, "fpt_inventory_inference_latest.json")

    if not os.path.exists(raw_json_path) or not os.path.exists(inference_json_path):
        print("⚠️ Chưa đủ dữ liệu JSON để tạo dashboard HTML.")
        return ""

    with open(raw_json_path, "r", encoding="utf-8") as f:
        products = json.load(f)
    with open(inference_json_path, "r", encoding="utf-8") as f:
        summary = json.load(f)

    # Đóng gói dữ liệu tối ưu đưa vào template HTML
    products_json_str = json.dumps(products, ensure_ascii=False)
    summary_json_str = json.dumps(summary, ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>FPT Retail & F.Studio - Executive Inventory Intelligence</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-primary: #0a0e17;
      --bg-secondary: #121826;
      --card-bg: rgba(26, 34, 52, 0.7);
      --card-border: rgba(255, 255, 255, 0.08);
      --accent-fpt: #cb1c22;
      --accent-fstudio: #2997ff;
      --accent-green: #10b981;
      --accent-amber: #f59e0b;
      --accent-red: #ef4444;
      --text-main: #f3f4f6;
      --text-muted: #9ca3af;
      --glass-blur: blur(16px);
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
        radial-gradient(at 100% 0%, rgba(41, 151, 255, 0.1) 0px, transparent 50%),
        radial-gradient(at 50% 100%, rgba(16, 185, 129, 0.05) 0px, transparent 50%);
      background-attachment: fixed;
    }}

    .container {{
      max-width: 1440px;
      margin: 0 auto;
    }}

    header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 24px;
      border-bottom: 1px solid var(--card-border);
      margin-bottom: 28px;
    }}

    .brand-title {{
      display: flex;
      align-items: center;
      gap: 14px;
    }}

    .badge-fpt {{
      background: linear-gradient(135deg, #cb1c22, #ea3a3d);
      color: white;
      font-weight: 800;
      font-size: 13px;
      padding: 6px 12px;
      border-radius: 8px;
      letter-spacing: 0.5px;
      box-shadow: 0 4px 12px rgba(203, 28, 34, 0.35);
    }}

    .badge-fstudio {{
      background: linear-gradient(135deg, #1e293b, #0f172a);
      border: 1px solid rgba(41, 151, 255, 0.4);
      color: #38bdf8;
      font-weight: 700;
      font-size: 13px;
      padding: 6px 12px;
      border-radius: 8px;
    }}

    h1 {{
      font-size: 24px;
      font-weight: 800;
      letter-spacing: -0.5px;
    }}

    .timestamp {{
      font-size: 13px;
      color: var(--text-muted);
    }}

    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
      margin-bottom: 28px;
    }}

    .kpi-card {{
      background: var(--card-bg);
      backdrop-filter: var(--glass-blur);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 20px;
      position: relative;
      overflow: hidden;
      transition: transform 0.2s, box-shadow 0.2s;
    }}

    .kpi-card:hover {{
      transform: translateY(-2px);
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
      border-color: rgba(255, 255, 255, 0.15);
    }}

    .kpi-title {{
      font-size: 13px;
      color: var(--text-muted);
      font-weight: 500;
      margin-bottom: 8px;
    }}

    .kpi-value {{
      font-size: 30px;
      font-weight: 800;
      letter-spacing: -1px;
    }}

    .kpi-sub {{
      font-size: 12px;
      color: var(--text-muted);
      margin-top: 6px;
    }}

    .val-green {{ color: #10b981; }}
    .val-blue {{ color: #38bdf8; }}
    .val-amber {{ color: #fbbf24; }}
    .val-red {{ color: #f87171; }}

    .toolbar {{
      background: var(--card-bg);
      backdrop-filter: var(--glass-blur);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 16px 20px;
      display: flex;
      flex-wrap: wrap;
      gap: 14px;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 20px;
    }}

    .search-box {{
      position: relative;
      flex: 1;
      min-width: 280px;
    }}

    .search-input {{
      width: 100%;
      background: rgba(15, 23, 42, 0.8);
      border: 1px solid var(--card-border);
      color: var(--text-main);
      padding: 10px 16px;
      border-radius: 10px;
      font-size: 14px;
      outline: none;
      transition: border-color 0.2s;
    }}

    .search-input:focus {{
      border-color: #38bdf8;
    }}

    .filter-pills {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }}

    .pill-btn {{
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--card-border);
      color: var(--text-muted);
      padding: 8px 16px;
      border-radius: 20px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }}

    .pill-btn:hover, .pill-btn.active {{
      background: rgba(41, 151, 255, 0.2);
      border-color: #38bdf8;
      color: #38bdf8;
    }}

    .table-container {{
      background: var(--card-bg);
      backdrop-filter: var(--glass-blur);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      overflow-x: auto;
      box-shadow: 0 12px 32px rgba(0, 0, 0, 0.4);
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 14px;
    }}

    th {{
      background: rgba(18, 24, 38, 0.95);
      padding: 14px 18px;
      color: var(--text-muted);
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      border-bottom: 1px solid var(--card-border);
    }}

    td {{
      padding: 14px 18px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.04);
      vertical-align: middle;
    }}

    tr:hover td {{
      background: rgba(255, 255, 255, 0.02);
    }}

    .status-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 700;
    }}

    .badge-in-stock {{
      background: rgba(16, 185, 129, 0.15);
      color: #34d399;
      border: 1px solid rgba(16, 185, 129, 0.3);
    }}

    .badge-low-stock {{
      background: rgba(245, 158, 11, 0.15);
      color: #fbbf24;
      border: 1px solid rgba(245, 158, 11, 0.3);
    }}

    .badge-out-of-stock {{
      background: rgba(239, 68, 68, 0.15);
      color: #f87171;
      border: 1px solid rgba(239, 68, 68, 0.3);
    }}

    .btn-view-stores {{
      background: rgba(56, 189, 248, 0.12);
      border: 1px solid rgba(56, 189, 248, 0.3);
      color: #38bdf8;
      padding: 6px 12px;
      border-radius: 8px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }}

    .btn-view-stores:hover {{
      background: #38bdf8;
      color: #0f172a;
    }}

    /* Modal */
    .modal-backdrop {{
      display: none;
      position: fixed;
      top: 0; left: 0; width: 100vw; height: 100vh;
      background: rgba(0, 0, 0, 0.75);
      backdrop-filter: blur(8px);
      z-index: 999;
      justify-content: center;
      align-items: center;
    }}

    .modal {{
      background: var(--bg-secondary);
      border: 1px solid var(--card-border);
      border-radius: 20px;
      width: 90%;
      max-width: 860px;
      max-height: 85vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6);
    }}

    .modal-header {{
      padding: 20px 24px;
      border-bottom: 1px solid var(--card-border);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}

    .modal-close {{
      background: none;
      border: none;
      color: var(--text-muted);
      font-size: 24px;
      cursor: pointer;
    }}

    .modal-body {{
      padding: 24px;
      overflow-y: auto;
    }}

    .store-list-item {{
      background: rgba(255, 255, 255, 0.02);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 14px 18px;
      margin-bottom: 10px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}

    .store-name {{
      font-weight: 700;
      font-size: 14px;
      margin-bottom: 4px;
    }}

    .store-addr {{
      font-size: 13px;
      color: var(--text-muted);
    }}

    .tag-fstudio {{
      background: rgba(41, 151, 255, 0.2);
      color: #38bdf8;
      padding: 2px 8px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 700;
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="brand-title">
        <span class="badge-fpt">FPT SHOP</span>
        <span class="badge-fstudio">F.STUDIO BY FPT</span>
        <h1>Executive Inventory Intelligence</h1>
      </div>
      <div class="timestamp">
        Cập nhật: <strong id="lbl-time">{summary.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M"))}</strong>
      </div>
    </header>

    <!-- KPI Section -->
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-title">TỔNG SKU APPLE THEO DÕI</div>
        <div class="kpi-value">{summary.get("total_skus", 0)}</div>
        <div class="kpi-sub">Bao phủ 5 hệ sinh thái Apple</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">TỶ LỆ SẴN HÀNG (AVAILABILITY)</div>
        <div class="kpi-value val-green">{summary.get("stock_rate_pct", 0)}%</div>
        <div class="kpi-sub">{summary.get("in_stock_count", 0)} SKU có hàng ngay</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">TỔNG MÁY TỒN KHẢ DỤNG</div>
        <div class="kpi-value val-blue">{summary.get("total_inventory_units", 0):,}</div>
        <div class="kpi-sub">Kho trung tâm + 602 Siêu thị</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">RỦI RO CẠN HÀNG (< 20 MÁY)</div>
        <div class="kpi-value val-amber">{summary.get("low_stock_count", 0)}</div>
        <div class="kpi-sub">Cần bổ sung điều chuyển gấp</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">ĐỨT HÀNG HOÀN TOÀN (ZERO STOCK)</div>
        <div class="kpi-value val-red">{summary.get("out_of_stock_count", 0)}</div>
        <div class="kpi-sub">Hết hàng toàn bộ 602 shop</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">SẴN SÀNG TẠI F.STUDIO</div>
        <div class="kpi-value val-blue">{summary.get("fstudio_available_count", 0)}</div>
        <div class="kpi-sub">Chuỗi ủy quyền cao cấp Apple</div>
      </div>
    </div>

    <!-- Toolbar Section -->
    <div class="toolbar">
      <div class="search-box">
        <input type="text" id="searchInput" class="search-input" placeholder="🔍 Tìm theo tên sản phẩm, mã SKU, dung lượng...">
      </div>
      <div class="filter-pills" id="categoryFilters">
        <button class="pill-btn active" data-cat="all">Tất Cả</button>
        <button class="pill-btn" data-cat="iPhone">iPhone</button>
        <button class="pill-btn" data-cat="MacBook">MacBook</button>
        <button class="pill-btn" data-cat="iPad">iPad</button>
        <button class="pill-btn" data-cat="Apple Watch">Apple Watch</button>
        <button class="pill-btn" data-cat="AirPods">AirPods</button>
      </div>
    </div>

    <!-- Table Section -->
    <div class="table-container">
      <table id="productTable">
        <thead>
          <tr>
            <th>Ngành Hàng</th>
            <th>Mã SKU</th>
            <th>Tên Sản Phẩm / Biến Thể</th>
            <th>Giá Niêm Yết</th>
            <th>Tồn Tổng</th>
            <th>FPT Shop</th>
            <th>F.Studio</th>
            <th>Trạng Thái</th>
            <th>Thao Tác</th>
          </tr>
        </thead>
        <tbody id="tableBody"></tbody>
      </table>
    </div>
  </div>

  <!-- Modal Chi Tiết Cửa Hàng -->
  <div class="modal-backdrop" id="storeModal">
    <div class="modal">
      <div class="modal-header">
        <h3 id="modalTitle">Danh Sách Cửa Hàng Còn Hàng</h3>
        <button class="modal-close" onclick="closeModal()">&times;</button>
      </div>
      <div class="modal-body" id="modalBody"></div>
    </div>
  </div>

  <script>
    const productsData = {products_json_str};

    let currentCategory = 'all';
    let currentSearch = '';

    function renderTable() {{
      const tbody = document.getElementById('tableBody');
      tbody.innerHTML = '';

      const filtered = productsData.filter(item => {{
        const matchCat = (currentCategory === 'all') || (item.category === currentCategory);
        const query = currentSearch.toLowerCase();
        const matchSearch = !query || 
          item.sku_name.toLowerCase().includes(query) || 
          item.sku_code.toLowerCase().includes(query) ||
          item.product_name.toLowerCase().includes(query);
        return matchCat && matchSearch;
      }});

      filtered.forEach((p, index) => {{
        const tr = document.createElement('tr');
        const priceStr = new Intl.NumberFormat('vi-VN', {{ style: 'currency', currency: 'VND' }}).format(p.price);
        
        let statusBadge = '';
        if (p.total_inventory_quantity === 0 && p.total_fpt_stores === 0) {{
          statusBadge = '<span class="status-badge badge-out-of-stock">Hết hàng</span>';
        }} else if (p.total_inventory_quantity < 20 || p.total_fpt_stores < 10) {{
          statusBadge = '<span class="status-badge badge-low-stock">Sắp hết (' + p.total_inventory_quantity + ')</span>';
        }} else {{
          statusBadge = '<span class="status-badge badge-in-stock">Có hàng</span>';
        }}

        tr.innerHTML = `
          <td><strong>${{p.category}}</strong></td>
          <td><code>${{p.sku_code}}</code></td>
          <td><a href="${{p.url}}" target="_blank" style="color: #f3f4f6; text-decoration: none; font-weight: 600;">${{p.sku_name}}</a></td>
          <td><strong>${{priceStr}}</strong></td>
          <td><strong style="color: #38bdf8;">${{p.total_inventory_quantity.toLocaleString()}}</strong></td>
          <td>${{p.total_fpt_stores}} shop</td>
          <td><span class="${{p.total_fstudio_stores > 0 ? 'tag-fstudio' : ''}}">${{p.total_fstudio_stores}} shop</span></td>
          <td>${{statusBadge}}</td>
          <td>
            <button class="btn-view-stores" onclick="openStoreModal(${{index}})">Xem Siêu Thị</button>
          </td>
        `;
        tbody.appendChild(tr);
      }});
    }}

    function openStoreModal(index) {{
      const p = productsData[index];
      const modal = document.getElementById('storeModal');
      const title = document.getElementById('modalTitle');
      const body = document.getElementById('modalBody');

      title.innerHTML = `Siêu Thị Có Hàng: ${{p.sku_name}}`;
      
      const stores = [...(p.fstudio_store_list || []), ...(p.fpt_store_list || [])];
      if (stores.length === 0) {{
        body.innerHTML = '<div style="text-align: center; color: var(--text-muted); padding: 40px;">Hiện tại không có siêu thị nào có sẵn máy tại quầy.</div>';
      }} else {{
        body.innerHTML = stores.map(s => `
          <div class="store-list-item">
            <div>
              <div class="store-name">
                [${{s.shopCode}}${{s.store_code ? ' | Tree: ' + s.store_code : ''}}] ${{s.shopName}}
                ${{s.cluster_group ? '<span style="background: rgba(245, 158, 11, 0.2); color: #fbbf24; padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: 700; margin-left: 6px;">Nhóm ' + s.cluster_group + '</span>' : ''}}
                ${{s.channel === 'F.Studio by FPT' ? '<span class="tag-fstudio" style="margin-left: 8px;">F.Studio</span>' : ''}}
              </div>
              <div class="store-addr">📍 ${{s.address}}</div>
            </div>
            <div>
              <span class="status-badge badge-in-stock">Sẵn hàng quầy</span>
            </div>
          </div>
        `).join('');
      }}

      modal.style.display = 'flex';
    }}

    function closeModal() {{
      document.getElementById('storeModal').style.display = 'none';
    }}

    window.onclick = function(event) {{
      const modal = document.getElementById('storeModal');
      if (event.target === modal) {{
        closeModal();
      }}
    }};

    document.getElementById('searchInput').addEventListener('input', (e) => {{
      currentSearch = e.target.value.trim();
      renderTable();
    }});

    document.querySelectorAll('#categoryFilters .pill-btn').forEach(btn => {{
      btn.addEventListener('click', (e) => {{
        document.querySelectorAll('#categoryFilters .pill-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentCategory = btn.getAttribute('data-cat');
        renderTable();
      }});
    }});

    renderTable();
  </script>
</body>
</html>
"""

    dashboard_file = os.path.join(REPORTS_DIR, "fpt_inventory_dashboard.html")
    with open(dashboard_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"✨ Đã xuất Dashboard HTML tương tác thành công: {dashboard_file}")
    return dashboard_file


if __name__ == "__main__":
    generate_html_dashboard()
