# 🔴 Viettel Store Inventory Intelligence

> **Hệ thống bóc tách, giám sát và phân tích tồn kho thực tế toàn diện Viettel Store (`viettelstore.vn`)**

---

## 🚀 Giới Thiệu Dự Án

`viettel-inventory-intelligence` là một engine độc lập được xây dựng để giải mã và khai thác trực tiếp các API ngầm của Viettel Store:
1. **Tổng số lượng tồn kho chính xác (`AmounInstock`)**: Truy vấn trực tiếp vào hệ thống ASMX ERP JSON-RPC để trích xuất số lượng máy thực tế có sẵn.
2. **Chi tiết điểm bán vật lý (Store-Level Stock)**: Quét danh sách hơn 400 siêu thị Viettel Store trên 63 tỉnh thành để xác định siêu thị nào đang còn hàng sẵn.
3. **Phân tích biến thể & giá bán đa tầng**: Tự động bóc tách mã UUID `Rule_ID`, mã SKU `Erp_Product_ID`, giá niêm yết, giá khuyến mãi và trạng thái đặt trước.
4. **Master Data 63 tỉnh thành**: Đồng bộ danh mục đơn vị hành chính và ánh xạ mã vùng ERP qua Customer Microservice Gateway.

---

## 📁 Cấu Trúc Thư Mục

```
viettel-inventory-intelligence/
├── README.md                                   # Tổng quan dự án & hướng dẫn sử dụng
├── config.py                                   # Cấu hình endpoint, headers, danh mục & đường dẫn
├── requirements.txt                            # Thư viện phụ thuộc (requests, beautifulsoup4, pandas...)
├── .gitignore                                  # Quy tắc loại trừ file tạm
├── docs/
│   └── VIETTEL_REVERSE_ENGINEERING_PLAYBOOK.md # Bách khoa toàn thư kỹ thuật & kiến trúc API ngầm
├── src/
│   ├── __init__.py
│   ├── client.py                               # ViettelStoreClient: Đóng gói toàn bộ các tầng API
│   ├── models.py                               # Dataclasses: ProductInfo, ProductVariant, StoreStock, ProvinceInfo
│   └── pipeline/
│       ├── __init__.py
│       └── scanner.py                          # ViettelScanner: Quét song song đa luồng
├── scripts/
│   ├── 01_sync_master_provinces.py             # Đồng bộ 63 tỉnh thành & mã ERP Viettel
│   ├── 02_probe_product_inventory.py           # Dò sâu tồn kho & danh sách siêu thị 1 sản phẩm
│   ├── 03_scan_catalog_inventory.py            # Quét hàng loạt danh mục sản phẩm (Apple Ecosystem)
│   ├── 04_generate_coverage_report.py          # Xuất báo cáo độ phủ & tồn kho (CSV & JSON)
│   └── 05_map_stores_to_personnel_tree.py      # Ánh xạ 163 siêu thị vào Cụm Nhân sự & sinh Viewer HTML
└── data/
    ├── master/                                 # Danh mục tỉnh thành & mapping siêu thị (viettel_store_mapping.json)
    ├── snapshots/                              # Snapshot dữ liệu theo phiên quét (viettel_inventory_latest.json)
    └── reports/                                # Báo cáo tổng hợp CSV & Viewer HTML tương tác
```

---

## ⚡ Hướng Dẫn Vận Hành

### 1. Đồng Bộ Master 63 Tỉnh Thành & Mã ERP
```bash
python3 scripts/01_sync_master_provinces.py
```

### 2. Dò Tồn Kho Chi Tiết 1 Sản Phẩm
```bash
# Dò bằng PID (ví dụ: iPhone 16 128GB hoặc iPhone 16 Pro Max)
python3 scripts/02_probe_product_inventory.py --pid 339614

# Hoặc dò bằng URL trực tiếp
python3 scripts/02_probe_product_inventory.py --url https://viettelstore.vn/dien-thoai/iphone-16-pro-max-pid339630.html
```

### 3. Quét Tồn Kho Hàng Loạt Toàn Hệ Thống Apple Ecosystem
```bash
# Quét toàn bộ 167 sản phẩm - 466 biến thể SKU Apple
python3 scripts/03_scan_catalog_inventory.py --all --concurrency 8
```

### 4. Tạo Báo Cáo Phân Tích Độ Phủ & Tồn Kho
```bash
python3 scripts/04_generate_coverage_report.py
```

### 5. Ánh Xạ Siêu Thị Vào Cây Nhân Sự Apple & Mở Viewer HTML
```bash
python3 scripts/05_map_stores_to_personnel_tree.py
```

Dữ liệu sẽ được tự động xuất ra:
* `data/reports/viettel_store_inventory_viewer.html`: **Giao diện Web tương tác tra cứu tồn kho theo Apple Store ID, Cụm nhân sự, chỉ số mật độ máy/shop & cấp độ sẵn hàng.**
* `data/reports/viettel_inventory_latest.csv`: Dữ liệu bảng phẳng chi tiết 466 SKU (màu, giá, tồn kho ERP, danh sách shop).
* `data/snapshots/viettel_inventory_latest.json`: Cấu trúc JSON phân cấp sâu.
* `data/reports/viettel_inventory_intelligence_summary.md`: Báo cáo tóm tắt chỉ số điều hành.

---

## 📖 Tài Liệu Kỹ Thuật Chuyên Sâu
Vui lòng xem file tài liệu chi tiết tại:  
[VIETTEL_REVERSE_ENGINEERING_PLAYBOOK.md](file:///Users/brucehuynh/GitHub/daily-promotion/viettel-inventory-intelligence/docs/VIETTEL_REVERSE_ENGINEERING_PLAYBOOK.md)

