# 📖 CELLPHONES INVENTORY INTELLIGENCE PLAYBOOK
> **Bách khoa toàn thư kỹ thuật, kiến trúc API ngầm & kinh nghiệm thực chiến bóc tách dữ liệu CellphoneS**  
> *Tác giả: CellphoneS Inventory Intelligence Team*  
> *Cập nhật lần cuối: Tháng 10/2026*

---

## 📑 MỤC LỤC
1. [Tổng Quan Kiến Trúc CellphoneS Gateway & Microservices](#1-tổng-quan-kiến-trúc-cellphones-gateway--microservices)
2. [Chi Tiết Các Endpoint API Ngầm & GraphQL v2 Backend](#2-chi-tiết-các-endpoint-api-ngầm--graphql-v2-backend)
3. [Cơ Chế Bóc Tách SSR Hydration (`window.__NUXT__`) & Tối Ưu Crawler](#3-cơ-chế-bóc-tách-ssr-hydration-windownuxt--tối-ưu-crawler)
4. [Cấu Trúc Dữ Liệu Giá Bán Đa Tầng & Đặc Quyền SMember](#4-cấu-trúc-dữ-liệu-giá-bán-đa-tầng--đặc-quyền-smember)
5. [Cơ Chế Tồn Kho & Chiến Lược Suy Luận Ngược (Stock Probing)](#5-cơ-chế-tồn-kho--chiến-lược-suy-luận-ngược-stock-probing)
6. [So Sánh Đối Đầu Kỹ Thuật: FPT Shop vs CellphoneS](#6-so-sánh-đối-đầu-kỹ-thuật-fpt-shop-vs-cellphones)
7. [Hướng Dẫn Vận Hành & Mở Rộng Dự Án Độc Lập](#7-hướng-dẫn-vận-hành--mở-rộng-dự-án-độc-lập)

---

## 1. TỔNG QUAN KIẾN TRÚC CELLPHONES GATEWAY & MICROSERVICES

Hệ thống bán lẻ thương mại điện tử CellphoneS (`cellphones.com.vn`) được xây dựng trên nền tảng **Nuxt.js (Vue SSR)** kết hợp cụm Microservices phân tán với API Gateway trung tâm tại:

* **Host Gateway:** `https://api.cellphones.com.vn`
* **Công nghệ truy vấn chính:** **GraphQL Gateway v2** kết hợp REST API chuyên trách.
* **Bản đồ dịch vụ nội bộ (Trích xuất từ runtime `env`):**
  * `api_service`: `https://api.cellphones.com.vn/`
  * `graphql_service`: `https://api.cellphones.com.vn/` (version `catalog_ver: "v2"`)
  * `graphql_service_product`: `https://api.cellphones.com.vn/`
  * `location_service`: `https://api.cellphones.com.vn/` (version `location_ver: "v1"`)
  * `cart_service`: `https://api.cellphones.com.vn/` (version `cart_ver: "v3"`)
  * `quote_ver`: `"v6"`, `payment_ver`: `"v4"`, `order_ver`: `"v6"`
  * `smember_service`: `https://api.smember.com.vn/`
  * `loyalty_service`: `https://api.smember.com.vn/loyalty/v2`
  * `sso_service`: `https://api.smember.com.vn/sso/v1`
  * `customer_service`: `https://customer.cps.onl/` (kèm JWT Bearer `token_customer_service`)
  * `sforum_service`: `https://api.sforum.vn/`

### Headers Yêu Cầu Tối Thiểu:
```python
HEADERS_COMMON = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": "https://cellphones.com.vn",
    "Referer": "https://cellphones.com.vn/",
    "Content-Type": "application/json",
}
```

---

## 2. CHI TIẾT CÁC ENDPOINT API NGẦM & GRAPHQL V2 BACKEND

### 2.1. API Truy Vấn Sản Phẩm, Biến Thể & Bảng Giá (Catalog & Pricing GraphQL)
* **Method:** `POST`
* **Endpoint:** `https://api.cellphones.com.vn/v2/graphql/query`
* **Query Cấu Trúc:**
```graphql
query getProductListByArrayId {
    products(
        filter: {
            static: {
                province_id: 30, # 30: TP.HCM, 70: Hà Nội
                product_id: ["59258", "90116", "90117"],
                stock: {
                    from: 0
                }
            }
        },
        size: 3
    ) {
        general {
            product_id
            url_path
            name
        }
        filterable {
            stock_available_id
            company_stock_id
            is_parent
            price
            prices
            special_price
            thumbnail
            stock
            categories
            promotion_information
        }
    }
}
```
* **Lưu ý kỹ thuật quan trọng:**
  * Tham số `product_id` **bắt buộc là mảng chuỗi (Array of Strings)**, ví dụ `["59258", "90116"]`. Nếu truyền số nguyên `[59258]` backend sẽ trả về mã lỗi `422 GRAPHQL_VALIDATION_FAILED`.
  * Tham số `size` phải tương ứng với số lượng ID trong mảng.

### 2.2. API Dynamic Banner & Dashboard Khuyến Mãi
* **Method:** `POST`
* **Endpoint:** `https://api.cellphones.com.vn/graphql-dashboard/graphql/query`
* **Các Query hỗ trợ:**
  * `BANNER_UD` / `MULTI_BANNER_UDS`: Lấy banner và deal theo mã chiến dịch (`ud`).
  * `banner_group(parent_product_id, province_id, member_rank)`: Trả về chính sách khuyến mãi cá nhân hoá theo tỉnh thành và hạng thành viên SMember.

---

## 3. CƠ CHẾ BÓC TÁCH SSR HYDRATION (`window.__NUXT__`) & TỐI ƯU CRAWLER

### 3.1. Điểm Yếu Của Crawler Dùng Trình Duyệt (Playwright / Selenium)
Phiên bản crawler cũ (`6-Apple_CPS_playwright.py`) sử dụng Playwright:
1. Mất 15 - 30 giây để render toàn bộ DOM nặng nề.
2. Phải mô phỏng click từng nút màu/dung lượng để đọc giá.
3. Phải click nút "Xem tất cả" mở Modal mới lấy được thông số kỹ thuật.
4. Tốn tài nguyên RAM/CPU rất lớn và dễ bị timeout.

### 3.2. Cơ Chế SSR Hydration State Bóc Tách Siêu Tốc
Trong kiến trúc Nuxt.js SSR của CellphoneS, mọi trang sản phẩm (`.html`) đều **chứa sẵn toàn bộ dữ liệu nghiệp vụ** trong thẻ script:
```html
<script>window.__NUXT__=(function(...){ return { state: { product: { productData: ... } } } })(...);</script>
```
* **Dữ liệu có sẵn mà không cần bấm click:**
  * `productData.general.product_id`: ID gốc của sản phẩm.
  * `productData.general.relation`: Mảng ID của tất cả các dung lượng liên kết (`[90116, 90117]`).
  * `productData.general.child_product`: Mảng ID biến thể màu sắc.
  * `productData.specification.basic`: Toàn bộ thông số phần cứng dạng cấu trúc `{ key, label, value }`.
  * `productData.filterable.prices`: Bảng giá SMember đầy đủ.
* **Hiệu năng đạt được:**
  * **Thời gian xử lý: < 200ms / 1 sản phẩm** (nhanh gấp **50 - 100 lần** so với Playwright).

---

## 4. CẤU TRÚC DỮ LIỆU GIÁ BÁN ĐA TẦNG & ĐẶC QUYỀN SMEMBER

Trường `filterable.prices` của CellphoneS trả về cơ cấu giá phân tầng chi tiết:

```json
{
  "root": {
    "value": 34990000,
    "discount_value": 0
  },
  "special": {
    "value": 30990000,
    "discount_value": 4000000
  },
  "snew": {
    "value": 30990000,
    "chiet_khau": 0
  },
  "smem": {
    "value": 30835000,
    "chiet_khau": 155000
  },
  "svip": {
    "value": 30680000,
    "chiet_khau": 310000
  }
}
```

* `root.value`: Giá niêm yết chính hãng từ Apple Việt Nam.
* `special.value`: Giá bán lẻ khuyến mãi công khai cho khách vãng lai.
* `snew.value`: Giá dành cho thành viên S-New.
* `smem.value`: Giá dành cho hạng S-Mem (chiết khấu thêm 0.5% - 1%).
* `svip.value`: Giá dành cho hạng S-VIP (chiết khấu thêm 1% - 2%).

---

## 5. CƠ CHẾ TỒN KHO & CHIẾN LƯỢC SUY LUẬN NGƯỢC (STOCK PROBING)

Khác với FPT Shop (để lộ số lượng tồn kho tổng qua trường `inventory`), CellphoneS **mask số lượng tuyệt đối về `0`** (`company_stock_quantity: 0`) để chống thu thập tình báo thương mại.

Tuy nhiên, CellphoneS để lộ thông tin qua **Mã trạng thái kho (State Machine)** và **Danh sách cửa hàng sẵn hàng**:

### 5.1. Bảng Trạng Thái Kho (`stock_available_id`):
* **`46`**: **Có hàng sẵn tại quầy (In-Stock Physical)** $\to$ Khách hàng có thể đến showroom nhận máy ngay.
* **`4920`**: **Hàng sắp về / Đặt trước (Pre-Order / In-Transit)** $\to$ Đang vận chuyển từ kho tổng hoặc đại lý uỷ quyền.
* **`43` / `48` / `56`**: **Tạm hết hàng hoặc hết hàng tại khu vực**.

> [!WARNING]
> **Cạm Bẫy Dữ Liệu Tĩnh / Cache ảo (Phantom Stock Bug):**
> Khi query danh mục qua `getProductListByArrayId`, mã sản phẩm cha (Parent Product ID, ví dụ `59258` cho iPhone 16 Pro Max 256GB) có thể mang cờ `stock_available_id: 46` do cache tĩnh từ catalog. **Tuy nhiên trên thực tế, máy có thể đã hết sạch hàng từ lâu!**  
> CellphoneS chỉ xác thực tồn kho vật lý thực tế qua 2 API thời gian thực bên dưới:

### 5.2. API Kiểm Tra Tỉnh/Thành Còn Hàng Toàn Quốc (`InstockProvinces`):
* **Endpoint:** `POST https://api.cellphones.com.vn/v2/graphql/query`
* **Query:**
```graphql
query InstockProvinces {
  instock_provinces_by_list(product_ids: [90169, 90170, 90171, 90172], company_id: 12869)
}
```
* **Ý nghĩa:**
  * Truyền danh sách `product_ids` của các biến thể con (Color/Capacity Child IDs).
  * Trả về danh sách các `province_id` đang còn hàng: `{"90169": [{"province_id": 1}, {"province_id": 30}], ...}`.
  * Nếu sản phẩm đã **hết hàng trên toàn quốc** (như trường hợp iPhone 16 Pro Max), API trả về `{}` (rỗng). Trên giao diện web, khối kiểm tra cửa hàng (`div[8]`) sẽ bị ẩn (`<!----> <!---->`).

### 5.3. API Danh Sách Cửa Hàng Còn Hàng Tại Quầy (`SHOP_STOCK`):
* **Endpoint:** `POST https://api.cellphones.com.vn/graphql-dashboard/graphql/query`
* **Query:**
```graphql
query SHOP_STOCK {
  shops_stock(productId: 90123, provinceId: 30) {
    district_id
    district_name
    province_id
    province_name
    shops {
      id
      external_id
      district_id
      province_id
      address
      phone
      near
      google_link
    }
  }
}
```
* **Ý nghĩa:**
  * Trả về danh sách chi tiết các **cửa hàng vật lý cụ thể** (địa chỉ, số điện thoại, tọa độ Google Maps) đang có sẵn sản phẩm tại tỉnh/thành được chọn.
  * Nếu tổng số `shops` $= 0$, sản phẩm hoàn toàn không có máy tại quầy ở tỉnh thành đó.

### 5.4. API Danh Mục Toàn Bộ Mạng Lưới Cửa Hàng (`GetDataMap4d`):
* **Endpoint:** `POST https://api.cellphones.com.vn/graphql-dashboard/graphql/query`
* **Query:**
```graphql
query getAllStores {
  GetDataMap4d(lat: 10.7914334, long: 106.687859) {
    shop {
      id
      code
      external_id
      address
      phone
      google_link
      district_id
      province_id
      latitude
      longitude
      company_id
    }
  }
}
```
* **Ý nghĩa:** Trích xuất toàn bộ **221 showroom vật lý của CellphoneS trên toàn quốc** (trong đó TP.HCM có 70 showroom, Hà Nội có 39 showroom...), lưu trữ offline tại [`data/master/cps_master_stores.json`](file:///Users/brucehuynh/GitHub/daily-promotion/cellphones-inventory-intelligence/data/master/cps_master_stores.json) làm mẫu số đối soát độ phủ.

### 5.5. Chiến Lược Suy Luận Ngược & Đo Lường Độ Phủ (Coverage Intelligence):
1. **Tầng Vĩ Mô (Độ phủ Tỉnh/Thành & Showroom):**
   * **Độ phủ Tỉnh/Thành Toàn Quốc:**
     $$\text{Nationwide Coverage} = \frac{\text{Số tỉnh/thành còn hàng từ } instock\_provinces\_by\_list}{63\text{ tỉnh/thành}} \times 100\%$$
   * **Độ phủ Showroom Khu Vực:**
     $$\text{Store Coverage} = \frac{\text{Số showroom còn hàng từ } shops\_stock}{\text{Tổng showroom mạng lưới tại tỉnh đó (VD: 70 ở TP.HCM)}} \times 100\%$$
2. **Quy tắc gắn nhãn sức khỏe tồn kho (Inventory Health Tiers):**
   * 🟢 **Dồi dào:** Độ phủ showroom $\ge 50\%$.
   * 🟡 **Trung bình:** Độ phủ showroom $20\% - 49\%$.
   * 🟠 **Hạn chế:** Độ phủ showroom $1\% - 19\%$.
   * 🔴 **Cháy hàng / Ảo:** $0$ showroom có hàng (kể cả khi catalog hiển thị mã 46).
3. **Tầng Vi Mô (Thăm dò giỏ hàng qua Binary Search):**
   * Đẩy số lượng $Q$ vào `cart_service` (`/v3/cart`) hoặc `quote_ver: "v6"`.
   * Bắt mã lỗi `has_zero_quantity_item` / `exceed_quantity` để dùng thuật toán tìm kiếm nhị phân chia đôi $[1, 200]$, xác định chính xác số lượng tồn kho trần của khu vực.

---

## 6. SO SÁNH ĐỐI ĐẦU KỸ THUẬT: FPT SHOP VS CELLPHONES

| Tiêu chí | FPT Shop & F.Studio | CellphoneS |
| :--- | :--- | :--- |
| **Kiến trúc Gateway** | REST BFF Gateway (`papi.fptshop.com.vn`) | GraphQL Gateway v2 & Dashboard Gateway (`api.cellphones.com.vn`) |
| **Phân luồng kênh** | `channel: "1"` (FPT Shop), `"12"` (F.Studio) | `company_id: 1` (CellphoneS), `7` (Điện Thoại Vui), `12869` (Retail) |
| **Tồn kho tổng toàn quốc** | ✅ Có API trả về con số chính xác (`inventory: 154`) | ❌ Bị che giấu (`company_stock_quantity: 0`) $\to$ Suy luận qua độ phủ showroom |
| **Tồn kho tại từng showroom** | Kiểm tra Boolean qua `/pickup-v2/check-shop` | Danh sách chi tiết địa chỉ/ĐT qua `shops_stock` |
| **Chính sách giá hội viên** | Giá đồng nhất (hoặc voucher FPT Privileges) | Chiết khấu phân cấp rõ ràng (`snew`, `smem`, `svip`) |
| **Tốc độ bóc tách sản phẩm** | ~100ms / request REST | ~100ms / GraphQL hoặc bóc tách `window.__NUXT__` |

---

## 7. HƯỚNG DẪN VẬN HÀNH & MỞ RỘNG DỰ ÁN ĐỘC LẬP

Thư mục `cellphones-inventory-intelligence` được đóng gói hoàn toàn độc lập với các công cụ chính:

### 7.1. Cài đặt môi trường:
```bash
pip install -r requirements.txt
```

### 7.2. Thăm dò tức thời 1 sản phẩm (CLI Probe):
```bash
python scripts/probe_product.py iphone-16-pro-max
# Thăm dò khu vực Hà Nội (Province ID: 70):
python scripts/probe_product.py iphone-16-pro-max --province 70
```

### 7.3. Đo lường độ phủ 1 dòng sản phẩm cụ thể:
```bash
python scripts/calculate_coverage.py iphone-16
python scripts/calculate_coverage.py iphone-15 --province 70
```

### 7.4. Chụp Snapshot danh mục vĩ mô:
```bash
python scripts/snapshot_macro_catalog.py
# Chụp riêng ngành hàng iPhone:
python scripts/snapshot_macro_catalog.py --category iPhone
```

### 7.5. Quét độ phủ showroom tự động toàn sàn:
```bash
# Quét độ phủ toàn bộ sản phẩm đang có hàng tại TP.HCM:
python scripts/scan_catalog_coverage.py

# Quét toàn bộ 310 SKU catalog (đối soát hàng ảo):
python scripts/scan_catalog_coverage.py --all

# Quét tại Hà Nội:
python scripts/scan_catalog_coverage.py --all --province 70
```

---

## 8. KẾT QUẢ THỰC NGHIỆM ĐỐI SOÁT (BENCHMARK DATASET)

Dữ liệu thực nghiệm thu thập ngày 08/10/2026 trên danh mục Apple (310 SKU, 822 biến thể màu/dung lượng):

1. **Tổng quan tồn kho thực tế tại TP.HCM (70 Showroom):**
   * **107 / 310 SKU (34.5%)** thực sự có sẵn máy tại các showroom.
   * **203 / 310 SKU (65.5%)** đã hết sạch hàng tại quầy.
   * **2 SKU dính cờ Cache Ảo:** *iPhone 16 Pro Max 256GB* và *Apple Watch Series 10 42mm (GPS)* mang mã catalog `46` nhưng thực tế có $0$ showroom còn máy.
2. **Độ phủ trung bình theo Ngành hàng:**
   * **AirPods:** 70.9% (TB 49.7 showroom/SKU)
   * **iPhone:** 53.2% (TB 37.2 showroom/SKU)
   * **Mac:** 20.9% (TB 14.6 showroom/SKU)
   * **iPad:** 15.9% (TB 11.1 showroom/SKU)
   * **Apple Watch:** 13.8% (TB 9.7 showroom/SKU)
3. **Các file dữ liệu đã xuất bản:**
   * [`data/reports/cps_coverage_latest.csv`](file:///Users/brucehuynh/GitHub/daily-promotion/cellphones-inventory-intelligence/data/reports/cps_coverage_latest.csv) (310 SKU)
   * [`data/snapshots/cps_snapshot_latest.json`](file:///Users/brucehuynh/GitHub/daily-promotion/cellphones-inventory-intelligence/data/snapshots/cps_snapshot_latest.json)
   * [`data/master/cps_master_stores.json`](file:///Users/brucehuynh/GitHub/daily-promotion/cellphones-inventory-intelligence/data/master/cps_master_stores.json) (221 Showroom)
