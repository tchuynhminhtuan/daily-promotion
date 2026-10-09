# 📖 PHONG VŨ INVENTORY REVERSE-ENGINEERING PLAYBOOK
> **Bách khoa toàn thư kỹ thuật, kiến trúc API ngầm & kinh nghiệm thực chiến bóc tách tồn kho Phong Vũ & Hệ sinh thái Teko**  
> *Tác giả: Daily Promotion Intelligence Team*  
> *Cập nhật lần cuối: Tháng 10/2026*

---

## 📑 MỤC LỤC
1. [Tổng Quan Kiến Trúc Phong Vũ & Hệ Sinh Thái Teko Core](#1-tổng-quan-kiến-trúc-phong-vũ--hệ-sinh-thái-teko-core)
2. [Cơ Chế Nạp Dữ Liệu Next.js (SSR & Data Endpoint)](#2-cơ-chế-nạp-dữ-liệu-nextjs-ssr--data-endpoint)
3. [Chi Tiết Các Hệ Thống API Microservices Ngầm](#3-chi-tiết-các-hệ-thống-api-microservices-ngầm)
4. [Nghiên Cứu Chuyên Sâu: Cơ Chế Trả Về Tồn Kho Tổng Của 1 SKU](#4-nghiên-cứu-chuyên-sâu-cơ-chế-trả-về-tồn-kho-tổng-của-1-sku)
   - 4.1. Tồn kho ở tầng Danh mục (`stockQuantity` trong `serverProducts`)
   - 4.2. Tồn kho ở tầng Chi tiết sản phẩm (`totalAvailable` trong `serverProduct`)
   - 4.3. Sự phân cấp: Hàng khan hiếm ($1, 2, 5\dots$) vs. Hàng dồi dào (Cap $1000$ / `None`)
   - 4.4. Các trường kho khác trong Schema (`warehouseStocks`, `siteStocks`, `status.sellable`)
5. [Chiến Lược Dò Tồn Kho Tuyệt Đối (Binary Search & Cart Probing)](#5-chiến-lược-dò-tồn-kho-tuyệt-đối-binary-search--cart-probing)
6. [Hướng Dẫn Crawl & Trích Xuất Dữ Liệu Tự Động](#6-hướng-dẫn-crawl--trích-xuất-dữ-liệu-tự-động)

---

## 1. TỔNG QUAN KIẾN TRÚC PHONG VŨ & HỆ SINH THÁI TEKO CORE

Khác với FPT Shop (tự phát triển PAPI gateway) hay CellphoneS (REST API truyền thống), website **Phong Vũ** (`phongvu.vn`) được xây dựng trên nền tảng thương mại điện tử do **Teko Vietnam** phát triển:

* **Frontend:** Next.js (SSR - Server-Side Rendering kết hợp React Client Hydration).
* **Backend:** Kiến trúc Microservices phân tán dưới domain `*.tekoapis.com`.
* **Mô hình phục vụ:** Backend for Frontend (BFF) kết hợp trực tiếp các services chuyên trách (Discovery, PPM, Cart, Payment, Location, IAM).

### Headers Yêu Cầu Tối Thiểu:
```python
HEADERS_COMMON = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": "https://phongvu.vn",
    "Referer": "https://phongvu.vn/",
}
```

---

## 2. CƠ CHẾ NẠP DỮ LIỆU NEXT.JS (SSR & DATA ENDPOINT)

Phong Vũ tận dụng tối đa cơ chế của Next.js:

### 2.1. Server-Side Rendering (Thẻ `__NEXT_DATA__`)
Khi client tải bất kỳ trang nào (ví dụ `https://phongvu.vn/c/san-pham-apple` hoặc `https://phongvu.vn/tai-nghe-apple-airpods-5--s260900725`), Next.js Server thực hiện `getServerSideProps`, gom dữ liệu từ các Teko microservices và nhúng sẵn dưới dạng JSON vào thẻ HTML:
```html
<script id="__NEXT_DATA__" type="application/json">
  {"props":{"pageProps":{ ... }}}
</script>
```
* **Lợi ích:** Crawler chỉ cần tải trang HTML, dùng Regex tách thẻ `<script id="__NEXT_DATA__">` là có ngay JSON nguyên vẹn của toàn bộ sản phẩm, giá, bộ lọc, phân trang mà không bị chặn API.

### 2.2. Next.js Client Data Endpoint (Pure JSON)
Khi client thực hiện routing SPA, Next.js gửi request lấy trực tiếp file JSON:
* **Category Listing:**
  ```http
  GET https://phongvu.vn/_next/data/{buildId}/default/desktop/c/{slug}.json?slug={slug}
  ```
* **Product Detail (PDP):**
  ```http
  GET https://phongvu.vn/_next/data/{buildId}/default/desktop/products/{sku}.json?sku={sku}
  ```
  *(Ví dụ: `https://phongvu.vn/_next/data/ho0A4eRsdUQzuDNcy_KDm/default/desktop/products/260901559.json?sku=260901559`)*
* Endpoint này trả về trực tiếp đối tượng `{"pageProps": ...}` sạch 100%, tốc độ phản hồi cực nhanh (< 200ms).

---

## 3. CHI TIẾT CÁC HỆ THỐNG API MICROSERVICES NGẦM

Qua việc phân tích `window.env` được nhúng trong mã nguồn máy khách Phong Vũ, hệ thống tích hợp các dịch vụ Teko sau:

| Tên Dịch Vụ | Base URL Endpoint | Chức Năng Nghiệp Vụ |
| :--- | :--- | :--- |
| **Product Discovery & Listing** | `https://discovery.tekoapis.com/api/v1`<br>`https://listing.tekoapis.com/api/` | Quản lý danh mục, cấu hình bộ lọc động theo ngành hàng, danh sách sản phẩm. |
| **Search Engine Service** | `https://search.tekoapis.com/api/search` | Tìm kiếm văn bản toàn diện (Access Token: `QUEYCPKVSKIDYGUCWPVBSCEWSCEZ6A`). |
| **PPM (Price & Promotion)** | `https://ppm.tekoapis.com/api/` | Bảng giá (`latestPrice`, `supplierRetailPrice`), chiết khấu, chương trình khuyến mãi, quà tặng (`gifts`). |
| **Location & Showroom** | `https://location.tekoapis.com/api/v1` (v2, v3) | Cây địa giới hành chính, danh sách showroom, định vị showroom gần nhất còn hàng. |
| **Cart & Checkout BFF** | `https://carts-consumer.tekoapis.com/`<br>`https://consumer-bff.tekoapis.com/api/v1` | Quản lý giỏ hàng, tính phí giao hàng, kiểm tra giới hạn tồn kho đơn hàng. |
| **Payment Gateway** | `https://payment-gateway.tekoapis.com/api/v2`<br>`https://payment-v2.tekoapis.com/api/v2` | Khởi tạo thanh toán trực tuyến, thẻ, VNPAY, trả góp qua thẻ tín dụng / VPBank. |
| **Smart Activation (Marketing)** | `https://smart-activation-discovery.tempi.vn/api/v1` | Popup, banner cá nhân hóa theo luồng người dùng (`_tempi_vp`, `_tempi_vs`). |
| **Identity & Access (IAM)** | `https://identity.tekoapis.com/api`<br>`https://users.tekoapis.com` | Xác thực người dùng, OTP điện thoại, quản lý hồ sơ khách hàng. |

---

## 4. NGHIÊN CỨU CHUYÊN SÂU: CƠ CHẾ TRẢ VỀ TỒN KHO TỔNG CỦA 1 SKU

> **Câu hỏi mấu chốt:** API của Phong Vũ có trả về thông tin **tồn kho tổng** của một SKU không?  
> **Trả lời:** **CÓ**, nhưng có cơ chế **phân cấp theo ngưỡng khan hiếm (Scarcity Threshold)**.

### 4.1. Tồn Kho Tại Tầng Danh Mục (`stockQuantity` trong `serverProducts`)
Khi gọi danh sách sản phẩm thuộc một danh mục (hoặc tìm kiếm), mỗi phần tử sản phẩm trả về trường `stockQuantity`:

```json
{
  "sku": "260901559",
  "name": "Ốp Lưng Silicon MagSafe cho iPhone 18 Pro - Đỏ Tía",
  "stockQuantity": 1,
  "price": { "latestPrice": 1290000 }
}
```

Dữ liệu thực nghiệm thu thập từ 40 sản phẩm Apple:
* SKU `260901559`: `stockQuantity = 1` (Chính xác tồn kho thật)
* SKU `260901549`: `stockQuantity = 2` (Chính xác tồn kho thật)
* SKU `260901552`: `stockQuantity = 5` (Chính xác tồn kho thật)
* SKU `260901537`: `stockQuantity = 1000` (Hàng dồi dào $\to$ bị Cap trần ở 1.000)
* SKU `260900725` (AirPods 5): `stockQuantity = 1000` (Hàng dồi dào)

### 4.2. Tồn Kho Tại Tầng Chi Tiết Sản Phẩm (`totalAvailable` trong `serverProduct.product`)
Khi truy vấn trang chi tiết sản phẩm (qua Next.js Data API: `/products/{sku}.json` hoặc HTML `__NEXT_DATA__`):

```json
{
  "pageProps": {
    "serverProduct": {
      "product": {
        "productInfo": { "sku": "260901559" },
        "totalAvailable": 1,
        "availableQuantity": null,
        "warehouseStocks": [],
        "siteStocks": [],
        "status": { "sellingCode": "", "sellable": true }
      }
    }
  }
}
```

* **Trường `totalAvailable`:**
  * **Nếu hàng khan hiếm ($\le 5$ hoặc ít hàng):** `totalAvailable` trả về **con số số lượng tồn kho tổng chính xác** (Ví dụ: `1`, `2`, `5`).
  * **Nếu hàng dồi dào (dư thừa tồn kho):** `totalAvailable` trả về `null` (hoặc `None`), đồng thời `status.sellable = true`. Lúc này hệ thống không giới hạn số lượng nhỏ cho người dùng.

### 4.3. Bảng Đối Chiếu Trạng Thái Tồn Kho

| Trường Hợp Tồn Kho | `serverProducts.stockQuantity` | `serverProduct.totalAvailable` | `status.sellable` | Ý Nghĩa Thực Tế |
| :--- | :---: | :---: | :---: | :--- |
| **Còn đúng 1 sản phẩm** | `1` | `1` | `true` | Khan hiếm nghiêm trọng, chỉ còn 1 cái trong toàn hệ thống. |
| **Còn rất ít (2 - 5 cái)** | `2` đến `5` | `2` đến `5` | `true` | Còn đúng con số hiển thị. |
| **Còn dồi dào** | `1000` (capped) | `null` | `true` | Kho tổng & các showroom có đầy đủ hàng ($\ge 10$ chiếc). |
| **Hết hàng** | `0` (hoặc ẩn) | `0` / `null` | `false` | Ngừng kinh doanh hoặc hết tồn kho toàn quốc. |

### 4.4. Các Trường Tồn Kho Khác Trong Schema Cần Lưu Ý
Trong đối tượng `product`, Teko thiết kế sẵn:
* `warehouseStocks`: Danh sách tồn tại các tổng kho trung tâm.
* `siteStocks`: Danh sách tồn tại các showroom bán lẻ vật lý.
* `availableQuantity`: Tồn kho phân bổ theo khu vực địa lý của người dùng (nếu có cookie vị trí).
* `purchaseStatus`: Trạng thái mua hàng (VD: PreOrder, Normal).

---

## 5. CHIẾN LƯỢC DÒ TỒN KHO TUYỆT ĐỐI (BINARY SEARCH & CART PROBING)

Nếu một sản phẩm hiển thị `stockQuantity = 1000` và bạn muốn biết **chính xác 100% số lượng tồn kho tổng vật lý** (ví dụ thực tế đang còn 42 chiếc hay 128 chiếc), ta áp dụng kỹ thuật **Cart Quantity Binary Search Probing**:

1. **Khởi tạo giỏ hàng phiên khách:**
   - Tạo giỏ hàng ẩn thông qua `https://carts-consumer.tekoapis.com/`.
2. **Thêm sản phẩm với số lượng giả định $Q$:**
   - Gửi yêu cầu cập nhật số lượng SKU với $Q = 50, 100, 200\dots$
3. **Phân tích lỗi phản hồi từ Cart Validation:**
   - Nếu số lượng $Q > \text{tồn kho thực tế}$, Teko Cart Engine sẽ từ chối và trả về:
     > `"Đơn hàng chứa sản phẩm đã hết tồn nên không thể tiếp tục thanh toán."`  
     hoặc  
     > `"Số lượng sản phẩm còn lại không đủ so với số sản phẩm bạn đã thêm vào Giỏ hàng."`
4. **Thuật toán tìm kiếm nhị phân $O(\log N)$:**
   - Với cận dưới $L = 1$, cận trên $R = 1000$, chỉ cần tối đa $\approx 10$ bước probe là xác định được **chính xác tuyệt đối số lượng tồn kho từng chiếc một**!

---

## 6. HƯỚNG DẪN CRAWL & TRÍCH XUẤT DỮ LIỆU TỰ ĐỘNG

### Cách 1: Query qua Next.js Data API (Nhanh nhất & Tinh khiết nhất)
```python
import requests

build_id = "ho0A4eRsdUQzuDNcy_KDm"
sku = "260901559"
url = f"https://phongvu.vn/_next/data/{build_id}/default/desktop/products/{sku}.json?sku={sku}"

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json"
}

r = requests.get(url, headers=headers)
data = r.json()

product = data["pageProps"]["serverProduct"]["product"]
print(f"SKU: {sku}")
print(f"Tồn kho tổng (totalAvailable): {product.get('totalAvailable')}")
print(f"Giá bán: {data['pageProps']['serverProduct']['priceAndPromotions']['price']:,} đ")
```

### Cách 2: Parse HTML Fallback (Không phụ thuộc `buildId`)
Nếu `buildId` thay đổi khi Phong Vũ deploy phiên bản web mới, chỉ cần fetch trực tiếp URL sản phẩm HTML và parse thẻ `__NEXT_DATA__`:

```python
import requests
import re
import json

url = "https://phongvu.vn/tai-nghe-apple-airpods-5--s260900725"
r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})

match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text)
if match:
    data = json.loads(match.group(1))
    new_build_id = data.get("buildId")
    product = data["props"]["pageProps"]["serverProduct"]["product"]
    print("BuildId mới nhất:", new_build_id)
```

---

## 7. BỘ SCRIPTS VẬN HÀNH THỰC TẾ

Hệ thống đã được đóng gói thành 3 script chuyên dụng trong thư mục `scripts/`:

1. **`01_crawl_total_inventory.py`**: Quét toàn bộ tồn kho tổng của tất cả các SKU trong danh mục (ví dụ `san-pham-apple`, `laptop`):
   ```bash
   python3 scripts/01_crawl_total_inventory.py --slug san-pham-apple --max-pages 5
   ```
2. **`02_probe_sku_single.py`**: Tra cứu chi tiết và trạng thái tồn kho tổng của 1 SKU:
   ```bash
   python3 scripts/02_probe_sku_single.py 260901559
   ```
3. **`03_probe_store_inventory.py`**: Dò tồn kho vật lý chính xác tại từng showroom Phong Vũ bằng thuật toán Binary Search Cart:
   ```bash
   # Dò tại 1 showroom cụ thể:
   python3 scripts/03_probe_store_inventory.py --sku 260901559 --store PV_HCM_01

   # Dò toàn bộ showroom tại TP.HCM hoặc Hà Nội:
   python3 scripts/03_probe_store_inventory.py --sku 260901559 --province "Hồ Chí Minh"
   ```

