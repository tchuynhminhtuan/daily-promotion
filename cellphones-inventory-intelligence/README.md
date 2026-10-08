# 📱 CellphoneS Inventory Intelligence

> **Hệ thống theo dõi, bóc tách và phân tích dữ liệu tồn kho, giá bán và đặc quyền hội viên CellphoneS qua Reverse-Engineered GraphQL Gateway & SSR Hydration.**

Dự án được xây dựng với cấu trúc **hoàn toàn độc lập (Self-Contained & Migration-Ready)**, sẵn sàng để xuất hoặc tách thành repository riêng biệt khi trưởng thành.

---

## ⚡ Điểm Nổi Bật (Highlights)

1. **Thay thế Playwright bằng Direct API & SSR Hydration:**
   - Tốc độ bóc tách sản phẩm tăng từ **15–30 giây/sản phẩm xuống còn < 200ms/sản phẩm** (nhanh hơn gấp 50–100 lần).
   - Tiết kiệm 95% RAM/CPU so với việc render Chromium headless.
2. **GraphQL Gateway v2 Integration:**
   - Tích hợp trực tiếp với endpoint `https://api.cellphones.com.vn/v2/graphql/query`.
   - Lấy trọn vẹn họ dòng sản phẩm, dung lượng liên kết (`relation`), bảng giá và cờ trạng thái kho trong 1 request duy nhất.
3. **Bóc tách cấu trúc giá SMember đa tầng:**
   - Hỗ trợ chiết khấu đầy đủ cho các hạng thành viên: **S-New**, **S-Mem**, **S-VIP**.
4. **Phân loại trạng thái kho vật lý:**
   - Nhận diện chính xác trạng thái sẵn hàng tại quầy (`stock_available_id: 46`), hàng sắp về / đặt trước (`stock_available_id: 4920`), hoặc tạm hết hàng.

---

## 📂 Cấu Trúc Dự Án (Project Structure)

```
cellphones-inventory-intelligence/
├── README.md                                   # Tài liệu hướng dẫn sử dụng tổng quan
├── config.py                                   # Cấu hình tập trung (Endpoints, Headers, Paths)
├── requirements.txt                            # Danh sách thư viện phụ thuộc tối thiểu
├── docs/
│   └── CELLPHONES_REVERSE_ENGINEERING_PLAYBOOK.md # Bách khoa toàn thư kỹ thuật API & Playbook
├── data/
│   ├── master/
│   │   ├── apple_product_slugs.json            # 188 slugs sản phẩm Apple chuẩn hoá
│   │   └── cps_master_provinces.json           # Danh mục mã tỉnh thành CellphoneS
│   ├── raw/                                    # Dữ liệu CSV thô theo mốc thời gian
│   ├── snapshots/                              # Snapshot JSON phục vụ đối soát biến động
│   └── reports/                                # Báo cáo và phân tích tự động
├── scripts/
│   ├── probe_product.py                        # CLI thăm dò tức thời 1 sản phẩm (< 1s)
│   └── snapshot_macro_catalog.py               # Pipeline chụp ảnh vĩ mô danh mục Apple
└── src/
    ├── __init__.py
    └── client.py                               # CPSApiClient với Connection Pooling & Retry
```

---

## 🚀 Hướng Dẫn Nhanh (Quickstart)

### 1. Cài đặt môi trường
```bash
cd cellphones-inventory-intelligence
pip install -r requirements.txt
```

### 2. Thăm dò tức thời 1 sản phẩm (CLI Probe)
```bash
# Thăm dò iPhone 16 Pro Max tại TP.HCM:
python scripts/probe_product.py iphone-16-pro-max

# Thăm dò tại Hà Nội (Province ID: 70):
python scripts/probe_product.py iphone-16-pro-max --province 70

# Thăm dò bằng URL đầy đủ:
python scripts/probe_product.py https://cellphones.com.vn/macbook-air-m2-2022-16gb.html
```

### 3. Chụp Snapshot danh mục vĩ mô
```bash
# Chụp nhanh toàn bộ danh mục Apple:
python scripts/snapshot_macro_catalog.py

# Chụp riêng danh mục iPhone:
python scripts/snapshot_macro_catalog.py --category iPhone
```

### 4. Quét Độ Phủ Showroom & Kiểm Tra Hàng Ảo (Coverage Intelligence)
```bash
# Quét độ phủ showroom toàn bộ sản phẩm đang có tồn kho tại TP.HCM (mặc định Province 30):
python scripts/scan_catalog_coverage.py

# Quét độ phủ toàn bộ sản phẩm tại Hà Nội (Province 70):
python scripts/scan_catalog_coverage.py --province 70

# Quét riêng ngành hàng iPhone:
python scripts/scan_catalog_coverage.py --category iPhone

# Quét kiểm tra độ phủ của một dòng sản phẩm cụ thể:
python scripts/calculate_coverage.py iphone-16
```
Báo cáo được tự động xuất ra:
* `data/reports/cps_coverage_latest.csv`
* `data/reports/cps_coverage_latest.json`


---

## 📖 Tài Liệu Chi Tiết
Để xem đầy đủ tài liệu phân tích kỹ thuật, bản đồ Microservices, cấu trúc GraphQL query và chiến lược bóc tách tồn kho, vui lòng tham khảo:  
👉 [CELLPHONES_REVERSE_ENGINEERING_PLAYBOOK.md](file:///Users/brucehuynh/GitHub/daily-promotion/cellphones-inventory-intelligence/docs/CELLPHONES_REVERSE_ENGINEERING_PLAYBOOK.md)
