# 📖 VIETTEL STORE INVENTORY INTELLIGENCE PLAYBOOK
> **Bách khoa toàn thư kỹ thuật, kiến trúc API ngầm & kinh nghiệm thực chiến bóc tách dữ liệu Viettel Store**  
> *Tác giả: Viettel Store Inventory Intelligence Team*  
> *Cập nhật lần cuối: Tháng 10/2026*

---

## 📑 MỤC LỤC
1. [Tổng Quan Kiến Trúc Viettel Store Gateway & Microservices](#1-tổng-quan-kiến-trúc-viettel-store-gateway--microservices)
2. [Tầng 1: ASMX Web Service - Tổng Tồn Kho Thực Tế & Giá Bán ERP](#2-tầng-1-asmx-web-service---tổng-tồn-kho-thực-tế--giá-bán-erp)
3. [Tầng 2: Store-Level Inventory Engine - Tồn Kho Từng Siêu Thị](#3-tầng-2-store-level-inventory-engine---tồn-kho-từng-siêu-thị)
4. [Tầng 3: Biến Thể, Cấu Hình & Ánh Xạ Mã ERP (Product Rules)](#4-tầng-3-biến-thể-cấu-hình--ánh-xạ-mã-erp-product-rules)
5. [Tầng 4: Async Component Engine - Danh Mục & Phân Trang Catalog](#5-tầng-4-async-component-engine---danh-mục--phân-trang-catalog)
6. [Tầng 5: Microservices Gateway Proxy (`customer-service`)](#6-tầng-5-microservices-gateway-proxy-customer-service)
7. [So Sánh Đối Đầu Kỹ Thuật: Viettel Store vs CellphoneS vs TGDD vs FPT Shop](#7-so-sánh-đối-đầu-kỹ-thuật-viettel-store-vs-cellphones-vs-tgdd-vs-fpt-shop)
8. [Hướng Dẫn Vận Hành & Khai Thác Dự Án](#8-hướng-dẫn-vận-hành--khai-thác-dự-án)

---

## 1. TỔNG QUAN KIẾN TRÚC VIETTEL STORE GATEWAY & MICROSERVICES

Hệ thống bán lẻ thương mại điện tử Viettel Store (`viettelstore.vn`) là một nền tảng **Hybrid Enterprise** quy mô lớn của Tập đoàn Công nghiệp – Viễn thông Quân đội (Viettel). Hệ thống tích hợp giữa kiến trúc backend **ASP.NET (C#)** truyền thống và cụm **Microservices REST API** hiện đại, kết nối trực tiếp với hệ sinh thái **ERP / SAP nội bộ**:

* **Host chính:** `https://viettelstore.vn`
* **CDN Tĩnh:** `https://cdn.viettelstore.vn`, `https://cdn1.viettelstore.vn` -> `cdn4`, `https://static.viettelstore.vn`
* **Công nghệ cốt lõi:**
  1. **ASMX JSON-RPC Web Service:** Giao tiếp trạng thái thời gian thực (Giá bán, tồn kho ERP, Coupon Viettel++).
  2. **Ajax Action Router:** Dispatcher xử lý các tác vụ kiểm tra kho hàng siêu thị, danh sách biến thể, gợi ý tìm kiếm.
  3. **Async Server-Side Rendering (SSR):** Engine trả về HTML components kết hợp gắn thẻ Google Tag Manager `dataLayer` chứa dữ liệu thương mại điện tử chuẩn hóa.
  4. **Customer Gateway Proxy:** Chuyển tiếp các truy vấn dữ liệu định danh người dùng và danh mục địa lý hành chính.

### Headers Yêu Cầu Tối Thiểu:
```python
HEADERS_COMMON = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": "https://viettelstore.vn",
    "Referer": "https://viettelstore.vn/",
    "X-Requested-With": "XMLHttpRequest",
}
```

---

## 2. TẦNG 1: ASMX WEB SERVICE - TỔNG TỒN KHO THỰC TẾ & GIÁ BÁN ERP

Đây là phát hiện đột phá nhất trong quá trình reverse engineering hệ thống Viettel Store: **Website công khai chính xác tổng số lượng tồn kho (Amount In Stock) thực tế trong kho ERP của Viettel**.

### Endpoint Tra Cứu Giá & Tồn Kho:
* **Method:** `POST`
* **Endpoint:** `https://viettelstore.vn/Site/_Sys/ajax.asmx/ProductRule_GetPriceByRule`
* **Content-Type:** `application/json; charset=utf-8`

### Payload Yêu Cầu:
```json
{
  "id": "d50cdf0c-aacc-438a-8702-faaa27e8d2d0",
  "pid": "339614"
}
```
* `pid` (`Product_ID`): ID định danh sản phẩm trên website (vd: `339614` cho iPhone 16 128GB).
* `id` (`Rule_ID`): UUID định danh biến thể màu sắc (lấy từ API bóc tách Rule ở Mục 4). Nếu để chuỗi rỗng `""`, API sẽ tự động trả về biến thể màu mặc định.

### Cấu Trúc Dữ Liệu Trả Về (Trích xuất thực tế):
```json
{
  "d": {
    "__type": "eViettel.WebPC.Site._Sys.ajax+AjaxResult",
    "stt": 1,
    "msg": null,
    "data": {
      "Price": "21990000",
      "SellPrice": "21990000",
      "AmounInstock": "64",
      "AmountMin": "0",
      "PriceDisplayType": "0",
      "Discount": "0",
      "SaleState": "0",
      "ProgramID": "",
      "Erp_Product_ID": "3110113000066"
    }
  }
}
```

### Giải Mã Các Trường Dữ Liệu:
| Trường | Kiểu dữ liệu | Ý nghĩa kỹ thuật |
| :--- | :--- | :--- |
| `AmounInstock` | `string (int)` | **Tổng số lượng máy tồn kho thực tế** (Ví dụ: `64` máy sẵn sàng bán). Nếu `0` nghĩa là hết hàng. |
| `Price` | `string (VND)` | Giá niêm yết của hãng / giá gốc trước khuyến mãi. |
| `SellPrice` | `string (VND)` | Giá bán lẻ áp dụng thực tế trên website. |
| `Erp_Product_ID` | `string` | **Mã SKU ERP nội bộ** (vd: `3110113000066`). Cực kỳ quan trọng để tiếp tục query kho siêu thị. |
| `SaleState` | `string (enum)` | `0`: Đang bán bình thường<br>`1`: Hết hàng (Đăng ký nhận tin khi về hàng)<br>`2`: Pre-order đặt cọc trước |
| `Discount` | `string (VND)` | Số tiền giảm giá trực tiếp theo rule. |
| `stt` | `int` | `1`: Thành công, `-1` hoặc `0`: Lỗi / biến thể không hợp lệ. |

---

## 3. TẦNG 2: STORE-LEVEL INVENTORY ENGINE - TỒN KHO TỪNG SIÊU THỊ

Khi khách hàng bấm vào nút "Xem siêu thị có hàng" trên trang chi tiết sản phẩm, hệ thống kích hoạt API truy vấn tồn kho tại từng chi nhánh theo thời gian thực.

### Endpoint Tra Cứu Tồn Kho Siêu Thị:
* **Method:** `POST`
* **Endpoint:** `https://viettelstore.vn/AjaxAction.aspx`
* **Content-Type:** `application/x-www-form-urlencoded; charset=UTF-8`

### Payload Yêu Cầu:
```urlencoded
action=get-markets-for-erp-checktonkho
provinceId=-1
districtId=0
productId=3110113000066
specCode=3110113000066
```
* `provinceId`: Mã tỉnh thành (`-1`: Quét toàn quốc, `1`: Hà Nội, `2`: TP.HCM...).
* `districtId`: `0` (quét toàn bộ quận huyện trong tỉnh).
* `productId` & `specCode`: Mã `Erp_Product_ID` lấy từ kết quả của Tầng 1.

### Cấu Trúc Dữ Liệu Trả Về (HTML Fragment):
Nếu siêu thị có hàng, API trả về danh sách các thẻ `item`:
```html
<div class="item " style="border-bottom: 1px dashed #d7d7d7;padding-top: 3px;padding-bottom: 3px;">
    <i class="fa fa-map-marker" style="margin-left:3px; margin-right: 5px;font-size: 20px;color: #ee0033"></i>
    HNI09 - HNI , P, 498 Xã Đàn, Phường Văn Miếu - Quốc Tử Giám, Thành phố Hà Nội - <span style="color: #13938E;">Còn hàng</span>
</div>
<div class="item " style="border-bottom: 1px dashed #d7d7d7;padding-top: 3px;padding-bottom: 3px;">
    <i class="fa fa-map-marker" style="margin-left:3px; margin-right: 5px;font-size: 20px;color: #ee0033"></i>
    HNI19 - HNI , P, 548 Trương Định., Phường Tương Mai, Thành phố Hà Nội - <span style="color: #13938E;">Còn hàng</span>
</div>
<div class="item " style="border-bottom: 1px dashed #d7d7d7;padding-top: 3px;padding-bottom: 3px;">
    <i class="fa fa-map-marker" style="margin-left:3px; margin-right: 5px;font-size: 20px;color: #ee0033"></i>
    PTO05 - PTO , P, Số 02 Mê Linh, Phường Vĩnh Phúc, Tỉnh Phú Thọ - <span style="color: #13938E;">Còn hàng</span>
</div>
```

### Quy Tắc Regex Bóc Tách:
Từ mỗi khối thẻ siêu thị, ta bóc tách được:
* **Store Code:** `HNI09`, `HNI19`, `PTO05` (Chuẩn hóa mã điểm bán Viettel).
* **Province Code:** `HNI` (Hà Nội), `PTO` (Phú Thọ), `HCM` (Hồ Chí Minh).
* **Store Address:** Địa chỉ chính xác của siêu thị.
* **Trạng thái:** `Còn hàng` hoặc `Tạm hết hàng`.
* *Trường hợp cạn hàng trên toàn khu vực:* API trả về `"Không tìm thấy Siêu Thị còn hàng tại khu vực bạn chọn!"`.

---

## 4. TẦNG 3: BIẾN THỂ, CẤU HÌNH & ÁNH XẠ MÃ ERP (PRODUCT RULES)

Để có được cặp mã `Rule_ID` và `Erp_Product_ID` cho từng màu sắc, hệ thống cung cấp API bóc tách bảng Rule sản phẩm.

* **Method:** `POST`
* **Endpoint:** `https://viettelstore.vn/AjaxAction.aspx`
* **Payload:**
  ```urlencoded
  action=get-list-rule-by-product
  productId=339614
  ```

### Dữ Liệu Trả Về & Thuộc Tính Trích Xuất:
```html
<ul class="option-color-product">
    <li>
        <label class="color-check active" id="d50cdf0c-aacc-438a-8702-faaa27e8d2d0" title="Đen">
            <input type="radio" data-erp="3110113000066" data-spec="IPHONE16128GB_DEN" />
            <div class="txt-color">Đen</div>
        </label>
    </li>
    <li>
        <label class="color-check " id="e09f5a3d-f208-438b-84b7-14ef773b7966" title="Trắng">
            <input type="radio" data-erp="3110113000063" data-spec="IPHONE16128GB_TRANG" />
            <div class="txt-color">Trắng</div>
        </label>
    </li>
</ul>
```
* `id` của label: Chính là **`Rule_ID`** dùng để gọi API Tầng 1.
* `data-erp`: Mã SKU ERP nội bộ dùng để gọi API Tầng 2.
* `data-spec`: Mã định danh thông số màu sắc.
* Cờ `disabled='disabled'` / `opacity: 0.4`: Báo hiệu màu này đã tạm hết hàng trên kênh online.

---

## 5. TẦNG 4: ASYNC COMPONENT ENGINE - DANH MỤC & PHÂN TRANG CATALOG

Để crawl toàn bộ danh mục sản phẩm (Catalog) mà không cần render trình duyệt giả lập, Viettel Store cung cấp endpoint Server-Side Component Async:

* **Method:** `POST`
* **Endpoint:** `https://viettelstore.vn/Site/_Sys/GetUserControlAsync.aspx`
* **Payload:**
  ```urlencoded
  path=ProductList5Col2026
  CatID=010001
  ManID=1
  PageSize=25
  CurrentPage=1
  SpecOrder=DangHot
### Danh Mục Category ID Chuẩn Của Hệ Sinh Thái Apple:
Viettel Store phân tách các dòng sản phẩm Apple theo các nhánh Category ID chuyên biệt (tất cả đều đi cùng `ManID=1` cho Apple):

| Nhánh sản phẩm | Category ID (`CatID`) | Sản phẩm tiêu biểu | Quy mô catalog |
| :--- | :--- | :--- | :--- |
| **iPhone** | `010001` | iPhone 18 Pro Max, 18 Pro, Duo, 17, 16, 15 | 31 items |
| **iPad** | `010003` | iPad Air M4 (11"/13"), iPad Pro M5, iPad Mini 7, iPad A16 | 35 items |
| **Apple Watch** | `010005023` | Apple Watch Series 12, Ultra 4, Ultra 3, Series 11, SE 3 | 63 items |
| **AirPods** | `010005005` | AirPods 5, AirPods 4 Chống Ồn, AirPods Pro 3, AirPods Max USB-C | 8 items |
| **Apple Pencil & PK**| `010005019` | Apple Pencil Pro, Apple Pencil USB-C, AirTag 2, Ví MagSafe | 5 items |
| **Sạc Cáp Apple** | `010005014` | Củ sạc 40W Dynamic 60W Max, Củ sạc 20W, Cáp 240W USB-C | 8 items |
| **Ốp Lưng Apple** | `010005012` | Ốp lưng MagSafe iPhone 18 Pro Max/Pro Clear & Silicone | 17 items |
| **TỔNG CỘNG** | — | **Toàn bộ hệ sinh thái phần cứng Apple chính hãng** | **167 items** |

### Cấu Trúc DataLayer Trả Về Trong HTML:
Hệ thống tự động inject khối dữ liệu Google Tag Manager `dataLayer` chứa JSON sạch:
```javascript
dataLayer.push({
    'event': 'view-Listing',
    'ecommerce': {
        'items': [
            {
                'item_id': '339630',
                'item_name': 'iPhone 16 Pro Max 256GB',
                'price': '34990000',
                'item_brand': 'Apple',
                'item_category': 'Điện thoại'
            }
        ]
    }
});
```
Crawler chỉ cần dùng regex trích xuất mảng `items` là có ngay danh mục sản phẩm chuẩn xác 100%.

---

## 6. TẦNG 5: HỆ THỐNG TRỢ LỰC TÀI CHÍNH, BUNDLE & VIỄN THÔNG (AFFORDABILITY & SERVICES)

Ngoài giá bán và số lượng tồn kho thuần túy, Viettel Store cung cấp 5 API dịch vụ phụ trợ cực kỳ giá trị để phân tích chiến lược giá và kích cầu:

### 6.1. API Khuyến Mại Đối Tác Thanh Toán (Payment & Bank Affordability)
* **Endpoint:** `POST https://viettelstore.vn/AjaxAction.aspx`
* **Payload:** `action=get-payment-promotion&ErpProductId=<Erp_Product_ID>`
* **Dữ liệu trả về:** Toàn bộ danh sách ưu đãi giảm giá và hoàn tiền khi thanh toán qua ngân hàng và cổng trả chậm:
  * Giảm 10% (tối đa 2.000.000đ) cho kỳ hạn 6, 9, 12 tháng qua Kredivo.
  * Hoàn tiền 20% (tối đa 500.000đ) khi mở mới thẻ TPBank EVO.
  * Ưu đãi giảm 500.000đ khi quẹt thẻ tín dụng MB Bank hoặc NCB từ 2.500.000đ.
  * Giảm 400.000đ thẻ Vikki Mastercard cho đơn từ 4.000.000đ.

### 6.2. API Mua Kèm Phụ Kiện Giá Sốc (Cross-sell Bundle ERP)
* **Endpoint:** `POST https://viettelstore.vn/AjaxAction.aspx`
* **Payload:** `action=get-list-product-buy-more-erp&erpProductId=<ERP_SKU>&productId=<PID>`
* **Dữ liệu trả về:** Danh mục sản phẩm bán kèm được giảm giá theo đơn hàng chính:
  * Giảm tới 2.000.000đ mua Flycam / Drone DJI khi mua cùng điện thoại.
  * Giảm tới 2.000.000đ mua kính AI Rokid.
  * Phụ kiện củ sạc, cáp sạc, sạc dự phòng giảm đến 50%.
  * Giảm 500.000đ mua loa bluetooth hàng hiệu (JBL, Harman Kardon, Edifier).
  * Giảm 10% ốp lưng, bao da và miếng dán màn hình.

### 6.3. API Bảng Thông Số Kỹ Thuật Toàn Diện (Tech Specs Sheet)
* **Endpoint:** `POST https://viettelstore.vn/AjaxAction.aspx`
* **Payload:** `action=get-product-special&productId=<PID>`
* **Dữ liệu trả về:** Bảng thông số phần cứng chi tiết:
  * Màn hình (Kích thước, tấm nền, tần số quét Super Retina XDR).
  * Camera trước/sau (Độ phân giải MP, khẩu độ, zoom quang học).
  * Chipset & CPU/GPU (Apple A-series, RAM/ROM).
  * Pin & Tiêu chuẩn sạc (MagSafe 25W, Qi2 15W, thời lượng giờ).
  * Xuất xứ và bảng phân bổ giá theo từng phiên bản màu sắc.

### 6.4. API Trợ Giá Gói Cước Viễn Thông Viettel (Telecom Subsidy)
* **Endpoint:** `POST https://viettelstore.vn/AjaxAction.aspx`
* **Payload:** `action=get-info-subsidy-detail-product&productId=<PID>&isdn=<Phone>&TimeCommitment=12`
* **Đặc quyền độc nhất:** Viettel Store cho phép trừ thẳng tiền máy cho khách hàng cam kết sử dụng gói cước di động Viettel (kỳ hạn 12 - 18 tháng).

### 6.5. API Điểm Thưởng Viettel++ (Loyalty Points)
* **Endpoint:** `POST https://viettelstore.vn/Site/_Sys/ajax.asmx/CheckAccountVTplus` & `GenCouponVTPlus`
* **Cơ chế:** Khách hàng đổi điểm tích lũy cước mạng Viettel để sinh mã coupon giảm giá trực tiếp vào đơn hàng.

---

## 7. TẦNG 6: MICROSERVICES GATEWAY PROXY (`customer-service`)

Viettel Store gom các microservices hiện đại thông qua Gateway `/Site/_Sys/ajax.aspx` với cờ phân quyền `a='customer-service'`.

* **Method:** `POST`
* **Endpoint:** `https://viettelstore.vn/Site/_Sys/ajax.aspx`
* **Tham số Request:**
  * `a`: `"customer-service"`
  * `methodName`: `"POST"` hoặc `"GET"`
  * `path`: URI định tuyến microservice
  * `requestBody`: Chuỗi JSON tham số (tối thiểu `"{}"`)

### Bảng Định Tuyến Microservices:
| Dịch vụ | Path Microservice | Chức năng & Dữ liệu trả về |
| :--- | :--- | :--- |
| **Province Master** | `/profile/v1/province/load` | Trả về danh sách 63 tỉnh thành chuẩn gồm `provinceId`, `provinceCode`, `erpProvinceId`. |
| **Ward Master** | `/profile/v1/province/ward/load` | Trả về danh sách phường xã (`requestBody: {"provinceId": 33}`). |
| **Customer Auth** | `/auth/v1/authentication/login/otp/send` | Gửi mã OTP đăng nhập số điện thoại. |
| **Warranty Info** | `/transaction/v1/customer/warranty` | Tra cứu thông tin bảo hành máy chính hãng Viettel. |
| **Order History** | `/transaction/v1/customer/transaction/detail` | Tra cứu chi tiết tiến độ đơn hàng. |

---

## 7. SO SÁNH ĐỐI ĐẦU KỸ THUẬT: VIETTEL STORE VS CELLPHONES VS TGDD VS FPT SHOP

| Tiêu chí | Viettel Store (`viettelstore.vn`) | FPT Shop (`fptshop.com.vn`) | Thế Giới Di Động (`thegioididong.com`) | CellphoneS (`cellphones.com.vn`) |
| :--- | :--- | :--- | :--- | :--- |
| **Kiến trúc cốt lõi** | ASP.NET + ASMX JSON-RPC | Next.js SSR + REST Microservices | Nuxt.js + REST API Internal | Nuxt.js + GraphQL Gateway v2 |
| **Tồn kho toàn quốc (ERP)** | ✅ **CÓ SẴN (`AmounInstock`)** | ✅ **CÓ SẴN (`inventory` trong `product/variant`)** | ❌ Ẩn (Chỉ suy luận qua cụm shop) | ❌ Ẩn (Chỉ có cờ Còn/Hết) |
| **Tồn kho chi tiết từng shop** | ❌ **Chỉ có cờ Còn/Hết** (danh sách shop khả dụng) | ❌ **Chỉ có cờ Còn/Hết** (`pickupType == 0`) | ❌ Chỉ có danh sách shop | ❌ Chỉ có danh sách shop |
| **Khả năng dò số tồn từng shop** | ❌ **Không khả thi** (Server bỏ qua biến `quantity`) | ✅ **Khả thi 100% (Binary Search qua `pick-up-at-shop`)** | ❌ Không khả thi | ❌ Không khả thi |
| **Mã định danh SKU** | ERP Product ID (`3110...`) | SKU ID & Code (`009...`) | Product ID & SKU ID | Product ID & Variant ID |
| **Cơ chế chống bot / Chặn IP** | Thấp - Trung bình (Headers chuẩn) | Trung bình (Akamai / Cloudflare 429) | Cao (Chặn IP, mã hóa 34 vùng tỉnh) | Trung bình (Rate-limit, Cloudflare) |
| **Tốc độ phản hồi API** | Cực nhanh (< 150ms) | Rất nhanh (< 200ms) | Trung bình (200 - 400ms) | Rất nhanh (< 100ms) |

---

## 8. CHUYÊN ĐỀ KỸ THUẬT: BÀI TOÁN DÒ TỒN KHO CHI TIẾT TỪNG SHOP BẰNG BINARY SEARCH (FPT SHOP VS VIETTEL STORE)

### 8.1. Cơ chế Tìm Kiếm Nhị Phân (Binary Search Cart Probing) trên FPT Shop
Tại sao FPT Shop lại cho phép chúng ta dò ra chính xác từng chiếc máy tại từng siêu thị riêng lẻ (vd: Shop 261 Khánh Hội còn đúng 3 máy)?
* **Nguyên lý API:** FPT Shop sở hữu Microservice `POST /api-data/checkout/api/Cart/GetShopPickupV2` (hoặc `/order-promising/pick-up-at-shop`).
* **Logic Backend:** Endpoint nhận mảng `product: [{"id": sku, "quantity": q, "isCheckInventory": true}]`. Backend thực hiện câu lệnh lọc:
  $$\text{Điều kiện hiển thị shop: } \text{PhysicalStock}_{\text{Shop}} \ge q$$
* **Thuật toán hội tụ:** Khi tăng $q$ lên vượt quá tồn thực tế của Shop X, Shop X sẽ **biến mất ngay lập tức** khỏi danh sách `pickupType == 0`. Nhờ tính chất đơn điệu (monotonicity), chúng ta áp dụng **Binary Search $O(\log N)$** với dải $[1 \dots 30]$ chỉ mất 4 - 5 request là xác định được số lượng máy tồn kho thực tế của shop.

### 8.2. Tại sao Viettel Store KHÔNG THỂ áp dụng cơ chế Binary Search này?
Qua quá trình dịch ngược toàn bộ mã nguồn JavaScript giỏ hàng (`Detail.js`, `cart.js`, `ShopCart.js`, `pdp-cart-ext.js`) và kiểm thử API:

1. **API Tồn Kho Siêu Thị (`get-markets-for-erp-checktonkho`):**
   * Tham số tiếp nhận: `productId` và `specCode` (ERP SKU ID).
   * Khi thực nghiệm bơm các tham số `quantity`, `amount`, `count`, `qty` từ $1 \to 500$, kết quả trả về **hoàn toàn giống nhau 100%** (`length = 393 bytes`).
   * **Kết luận:** Backend C# / SQL của Viettel Store chỉ chạy logic kiểm tra nhị phân: `WHERE ErpProductId = ... AND Stock > 0`. Hệ thống hoàn toàn bỏ qua tham số số lượng yêu cầu.
2. **Luồng Giỏ Hàng & Checkout Viettel Store:**
   * Viettel Store xây dựng giỏ hàng theo cơ chế **ASP.NET Session** phía server (`AjaxSession.aspx`).
   * Ở bước chọn siêu thị nhận hàng (`at-market`), hàm `getMarket11()` chỉ gọi `action=get-markets-by-ward` với `provinceId` và `wardId` để **tải danh bạ tất cả các điểm bán trên địa bàn**, hoàn toàn không gửi kèm `productId`, `specCode` hay `quantity` để kiểm tra khả năng đáp ứng theo thời gian thực.
   * Viettel Store không có cơ chế `order-promising` trên web client-side; việc kiểm tra và điều chuyển máy được thực hiện nội bộ sau khi đơn hàng được tạo.

### 8.3. Giải Pháp Tối Ưu Cho Viettel Store: Trí Tuệ Mật Độ Phân Bổ (Inventory Density & Availability Tiers)
Không cần tốn hàng ngàn request dò nhị phân (vốn dễ gây quá tải và nghẽn mạng), hệ thống Viettel Store cung cấp trực tiếp 2 giá trị cốt lõi:
1. **Tổng tồn kho ERP toàn quốc (`AmounInstock`):** Chính xác 100% đến từng máy trên toàn quốc.
2. **Độ phủ siêu thị (`stores_count`):** Danh sách toàn bộ các shop đang có hàng.

Từ đó, công cụ tính toán:
* **Mật độ tồn kho trung bình:** $\text{Mật độ} = \frac{\text{AmounInstock}}{\text{stores\_count}}$ (vd: 245 máy / 112 shop $\approx 2.2$ máy/shop).
* **Cấp độ sẵn hàng (Availability Tier):**
  * 🟢 **Dồi dào ($\ge 300$ máy toàn quốc):** Sẵn nhiều máy mới nguyên seal tại shop.
  * 🔵 **Tiêu chuẩn ($50 - 300$ máy toàn quốc):** Phân bổ đều, mỗi shop thường có từ $1 - 3$ máy.
  * 🔴 **Hàng hiếm ($< 50$ máy hoặc $< 30$ shop):** Rất khan hiếm, mỗi shop trong danh sách thường chỉ còn $1$ máy hoặc phải điều chuyển.

---

## 9. HƯỚNG DẪN VẬN HÀNH & KHAI THÁC DỰ ÁN

Dự án `viettel-inventory-intelligence` được tổ chức độc lập và cung cấp các script thực thi nhanh:

```bash
# 1. Đồng bộ master data 63 tỉnh thành & mã ERP Viettel
python3 scripts/01_sync_master_provinces.py

# 2. Dò tồn kho chi tiết 1 sản phẩm (vd: iPhone 16 Pro Max hoặc iPhone 16)
python3 scripts/02_probe_product_inventory.py --pid 339614

# 3. Quét toàn bộ danh mục Apple Ecosystem Viettel Store (167 sản phẩm - 466 biến thể SKU)
python3 scripts/03_scan_catalog_inventory.py --concurrency 8

# 4. Xuất báo cáo tồn kho & độ phủ siêu thị (CSV & JSON)
python3 scripts/04_generate_coverage_report.py

# 5. Đối soát 163 siêu thị vào Cây nhân sự Apple & sinh Viewer HTML tương tác
python3 scripts/05_map_stores_to_personnel_tree.py
```

