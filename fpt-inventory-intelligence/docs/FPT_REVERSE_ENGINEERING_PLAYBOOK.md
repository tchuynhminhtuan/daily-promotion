# 📖 FPT RETAIL INVENTORY REVERSE-ENGINEERING PLAYBOOK
> **Bách khoa toàn thư kỹ thuật, kiến trúc API ngầm & kinh nghiệm thực chiến bóc tách tồn kho FPT Shop & F.Studio by FPT**  
> *Tác giả: FPT Inventory Intelligence Team*  
> *Cập nhật lần cuối: Tháng 10/2026*

---

## 📑 MỤC LỤC
1. [Tổng Quan Kiến Trúc FPT Gateway & PAPI Backend](#1-tổng-quan-kiến-trúc-fpt-gateway--papi-backend)
2. [Chi Tiết Các Endpoint API Ngầm Quan Trọng](#2-chi-tiết-các-endpoint-api-ngầm-quan-trọng)
3. [Cơ Chế Bảo Vệ WAF Cloudflare & Chiến Lược Vượt Rate Limit](#3-cơ-chế-bảo-vệ-waf-cloudflare--chiến-lược-vượt-rate-limit)
4. [Thuật Toán Dò Tồn Kho Vật Lý $O(\log N)$ (Binary Search Probing)](#4-thuật-toán-dò-tồn-kho-vật-lý-olog-n-binary-search-probing)
5. [Bài Học Thực Chiến: Mô Hình Co-location / Shop-in-Shop (Garmin vs FPT Shop)](#5-bài-học-thực-chiến-mô-hình-co-location--shop-in-shop-garmin-vs-fpt-shop)
6. [Mô Hình Hybrid 2 Tầng (Vĩ Mô Toàn Quốc & Vi Mô Theo Yêu Cầu)](#6-mô-hình-hybrid-2-tầng-vĩ-mô-toàn-quốc--vi-mô-theo-yêu-cầu)
7. [Hệ Thống Phân Tích Biến Động Chuỗi Thời Gian (Time-Series Delta Intelligence)](#7-hệ-thống-phân-tích-biến-động-chuỗi-thời-gian-time-series-delta-intelligence)
8. [Hướng Dẫn Triển Khai Độc Lập & Mở Rộng Hệ Thống](#8-hướng-dẫn-triển-khai-độc-lập--mở-rộng-hệ-thống)

---

## 1. TỔNG QUAN KIẾN TRÚC FPT GATEWAY & PAPI BACKEND

FPT Retail vận hành hệ thống thương mại điện tử qua API Gateway trung tâm tại:
* **Host Gateway:** `https://papi.fptshop.com.vn`
* **Kiến trúc:** BFF (Backend for Frontend) kết hợp Microservices phục vụ cả Web và App mobile.
* **Cơ chế Phân Luồng Kênh (Multi-Tenant by Channel):**
  * `orderChannel: "1"` hoặc `channel: "1"` $\to$ Chuỗi **FPT Shop** thông thường.
  * `orderChannel: "12"` hoặc `channel: "12"` $\to$ Chuỗi **F.Studio by FPT** (Apple Premium Reseller).
  * `channel: "garmin"` / shop có feature code `6` $\to$ Chuỗi **Garmin Brand Agency**.

### Headers Yêu Cầu Tối Thiểu:
```python
HEADERS_COMMON = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": "https://fptshop.com.vn",
    "Referer": "https://fptshop.com.vn/",
    "Content-Type": "application/json"
}
```

---

## 2. CHI TIẾT CÁC ENDPOINT API NGẦM QUAN TRỌNG

### 2.1. API Lấy Biến Thể & Tồn Kho Tổng Hệ Thống (Central Inventory API)
* **Method:** `GET`
* **Endpoint:** `https://papi.fptshop.com.vn/gw/v1/public/bff-before-order/product/variant`
* **Query Params:** `slug={product_slug}` (Ví dụ: `dien-thoai/iphone-17-pro-max`)
* **Dữ liệu trả về:**
  * Toàn bộ danh sách SKU (mã code, tên màu sắc, dung lượng, giá bán).
  * `inventory`: **Số lượng tồn kho tổng khả dụng của toàn quốc**.
  * `type`: Trạng thái kinh doanh (`Normal`, `PreOrder`, `StopBusiness`).

### 2.2. API Kiểm Tra Tồn Kho Theo Siêu Thị / Tỉnh Thành (Smart Pickup API)
* **Method:** `POST`
* **Endpoint:** `https://papi.fptshop.com.vn/gw/api/v1/pickup-v2/check-shop`
* **Payload cấu trúc:**
```json
{
  "cityCode": "79",
  "orderDoctotal": 34990000,
  "product": [
    {
      "id": "00921800",
      "name": "iPhone 17 Pro Max 256GB Cam Vũ Trụ",
      "quantity": 1,
      "price": 34990000,
      "unit": 8,
      "isCheckInventory": true
    }
  ]
}
```
* **Ý nghĩa phản hồi từ API:**
  * Mảng `data`: Danh sách các siêu thị trong tỉnh được chỉ định.
  * `pickupType == 0`: **SẴN HÀNG LẤY NGAY TẠI QUẦY** (Kho vật lý của siêu thị đang có $\ge$ `quantity` chỉ định).
  * `pickupType != 0` (thường là 1 hoặc 2): **KHÔNG CÓ HÀNG SẴN** (phải điều phối/chuyển kho hoặc giao hàng từ kho tổng sau 1-3 ngày).

---

## 3. CƠ CHẾ BẢO VỆ WAF CLOUDFLARE & CHIẾN LƯỢC VƯỢT RATE LIMIT

### 3.1. Hiện Tượng Cloudflare Rate Limiting (WAF IP Reputation Throttling)
FPT Shop đặt toàn bộ `papi.fptshop.com.vn` sau **Cloudflare WAF**. Khi client mở quá nhiều luồng (ví dụ $\ge 12$ threads) bắn dồn dập $\ge 50$ req/giây:
* Cloudflare sẽ tạm thời đưa IP vào danh sách chặn tạm (15–30 phút).
* Trả về mã lỗi: **`HTTP 403 Forbidden`** hoặc **`HTTP 429 Too Many Requests`**.
* **BẪY LỖI KINH ĐIỂN (False Negative Bug):**
  * Nếu code xử lý: `if r.status_code != 200: return False`.
  * Khi gặp lỗi 403, code nhầm tưởng siêu thị "không đủ hàng", lập tức gán kết quả là **1 máy** cho toàn bộ danh mục sản phẩm!

### 3.2. Giải Pháp Xử Lý Triệt Để Trong Production:
1. **Khống chế số luồng an toàn (Concurrency Throttling):**
   * Không bao giờ vượt quá **4 – 6 luồng** song song cho một địa chỉ IP client.
2. **Exponential Backoff & Jitter khi gặp 403 / 429:**
```python
if r.status_code in [403, 429]:
    sleep_time = 2.0 * (attempt + 1)
    time.sleep(sleep_time)
    continue # Retry lại, tuyệt đối KHÔNG trả về False
```
3. **Phân Luồng Kênh Thông Minh (Smart Channel Filtering):**
   * Nếu shop mục tiêu là FPT Shop $\to$ Chỉ gửi request `HEADERS_FPTSHOP` (bỏ request F.Studio).
   * Giảm ngay **50% số lượng request** gửi lên server.
4. **Connection Pooling:**
   * Sử dụng `requests.Session` với `HTTPAdapter(pool_connections=25, pool_maxsize=25)` giúp tái sử dụng TCP handshake / TLS session, giảm tải cho Cloudflare edge.

---

## 4. THUẬT TOÁN DÒ TỒN KHO VẬT LÝ $O(\log N)$ (BINARY SEARCH PROBING)

### 4.1. Vấn Đề
API của FPT **không bao giờ trả về con số tồn kho cụ thể của siêu thị** (ví dụ "shop này còn 20 máy"). API chỉ trả về Boolean: *"Tại shop này, số lượng $Q$ có lấy ngay được không?"*

### 4.2. Thuật Toán Tìm Kiếm Nhị Phân (Binary Search)
Thay vì nhích tuyến tính $Q = 1 \to 2 \to 3 \dots$ (tốn $N$ request), ta áp dụng thuật toán tìm kiếm nhị phân chia đôi trên khoảng $[low, high]$:
* Khởi tạo $low = 1, high = 30$ (hoặc cận trên là tồn kho tổng của SKU).
* Kiểm tra điểm giữa $mid = \lfloor (low + high + 1) / 2 \rfloor$:
  * Nếu `check_qty(mid) == True`: Cửa hàng có ít nhất $mid$ máy $\to$ Thu hẹp khoảng tìm kiếm lên nửa trên: $low = mid$.
  * Nếu `check_qty(mid) == False`: Cửa hàng có ít hơn $mid$ máy $\to$ Thu hẹp khoảng tìm kiếm xuống nửa dưới: $high = mid - 1$.
* Lặp lại cho đến khi $low == high$.

### 4.3. Minh Chứng Thực Nghiệm:
Ví dụ với SKU `iPhone 17 Pro Max 256GB Cam Vũ Trụ` (tồn thực tế: **20 máy** tại shop 155 Nguyễn Thái Học):
```
Bước 1: check_qty(2)  -> True  (Xác nhận có >= 2 máy, kích hoạt Binary Search [2, 30])
Bước 2: mid = 16      -> True  (Có >= 16 máy -> khoảng mới [16, 30])
Bước 3: mid = 23      -> False (Ít hơn 23 máy -> khoảng mới [16, 22])
Bước 4: mid = 19      -> True  (Có >= 19 máy -> khoảng mới [19, 22])
Bước 5: mid = 21      -> False (Ít hơn 21 máy -> khoảng mới [19, 20])
Bước 6: mid = 20      -> True  (Chính xác là 20 máy!)
```
👉 **Chỉ mất 6 request (~1.2 giây)** để tìm chính xác số lượng 20 máy thay vì 20 request!

---

## 5. BÀI HỌC THỰC CHIẾN: MÔ HÌNH CO-LOCATION / SHOP-IN-SHOP (GARMIN VS FPT SHOP)

### 5.1. Bối Cảnh
Tại các mặt bằng vàng (như *155 Nguyễn Thái Học - Vũng Tàu, 318 Lê Duẩn - Đà Nẵng, 350 Minh Khai - Hà Nội, 198B Đường 3/2 - Cần Thơ*):
* FPT Retail vận hành 2 pháp nhân / quầy bán hàng tại cùng một địa chỉ:
  1. **FPT Shop chuẩn:** Bán Apple, Samsung, Laptop (ví dụ `30841`).
  2. **Garmin Brand Agency:** Chỉ bán đồng hồ và phụ kiện thể thao Garmin (ví dụ `31604`).
* Cả 2 shop đều chung số nhà, tên đường, quận huyện, tỉnh thành.

### 5.2. Lỗi Mapping Chữ Viết Đơn Thuần
* Thuật toán so khớp text (Fuzzy Matching) tính điểm dựa trên số nhà và tên đường. Cả 2 shop đạt điểm trùng khớp bằng nhau 100%.
* Do shop Garmin xuất hiện trước trong mảng dữ liệu, shop Garmin **đã giành mất mã Apple của FPT Shop**.
* Hệ quả: Khi probe ngành hàng Apple tại shop Garmin, kết quả trả về luôn là **0 máy** vì shop Garmin không được cấp quota Apple!

### 5.3. Giải Pháp Kỹ Thuật Đã Triển Khai:
Bóc tách 3 trường metadata độc quyền của FPT:
1. `shopFeatures`: Shop Garmin chỉ có `[{'code': '6', 'name': 'Garmin'}]`. FPT Shop chuẩn có `[{'code': '1', 'name': 'FPTShop'}, {'code': '10', 'name': 'Trung Tâm Laptop'}]`.
2. `shopName`: Tiền tố `G-` (ví dụ `BAR G-155...`).
3. `displayAddress`: Hậu tố `(Garmin Store)`.

**Luật trong Matching Engine:**
* Trừ **`-100 điểm phạt`** nếu shop ứng viên là Garmin đối với luồng dữ liệu Apple.
* Thưởng **`+30 điểm ưu tiên`** cho shop có feature `FPTShop` hoặc `F.Studio`.
* Tự động kiểm tra Smoke-test: Nếu shop probe Apple ra 0 máy, tự động tìm shop song sinh cùng địa chỉ để cảnh báo redirect.

---

## 6. MÔ HÌNH HYBRID 2 TẦNG (VĨ MÔ TOÀN QUỐC & VI MÔ THEO YÊU CẦU)

Thay vì chạy **DEEP AUDIT cồng kềnh (54 phút)** để quét toàn bộ 602 siêu thị x 482 SKU, kiến trúc tối ưu phân thành 2 tầng độc lập:

| Đặc tính | ⚡ TẦNG 1: VĨ MÔ TOÀN QUỐC (FAST MODE) | 🎯 TẦNG 2: VI MÔ THEO YÊU CẦU (ON-DEMAND PROBER) |
| :--- | :--- | :--- |
| **Phạm vi** | 482 SKU Apple toàn quốc (kho tổng) | 1 Siêu thị cụ thể (Chỉ định theo mã hoặc địa chỉ) |
| **Thời gian chạy** | **~9.6 giây** | **~20 – 35 giây** |
| **Phương pháp** | Quét song song `variant API` lấy `total_inventory` | Single-Province Pickup Scan + Binary Search $O(\log N)$ |
| **Tần suất chạy** | Tự động 3 lần/ngày (7h, 12h, 21h) | Bất kỳ lúc nào người dùng hoặc quản lý yêu cầu |
| **Sự phụ thuộc** | Độc lập 100% | Độc lập 100% (không cần DEEP AUDIT) |

---

## 7. HỆ THỐNG PHÂN TÍCH BIẾN ĐỘNG CHUỖI THỜI GIAN (TIME-SERIES DELTA INTELLIGENCE)

### 7.1. Chu Kỳ Đo 3 Lần / Ngày
* **07:00 (Mở ngày):** Nhập hàng ban đêm (Night Restock) từ Apple và kho tổng.
* **12:00 (Giữa ngày):** Tốc độ tiêu thụ ca sáng.
* **21:00 (Chốt ngày):** Giờ vàng mua sắm ca tối & tổng kết 24h.

### 7.2. Công Thức & Chỉ Số Delta
So sánh 2 snapshot $T_1$ và $T_2$ ($\Delta = Q_{T_2} - Q_{T_1}$):
* **Nếu $\Delta < 0$ (Giảm tồn kho):**
  * $\text{Lượng máy bán ra} = |\Delta|$
  * $\text{Doanh thu ước tính} = |\Delta| \times \text{Đơn giá SKU}$
* **Nếu $\Delta > 0$ (Tăng tồn kho):**
  * $\text{Lượng máy nhập thêm (Restock)} = \Delta$
* **Nếu $\Delta == 0$:**
  * Hàng tồn đọng / không có giao dịch trong ca.

### 7.3. Các Công Cụ Đã Xây Dựng:
* `scripts/automation/auto_macro_snapshot.py`: Tự động chụp và lưu snapshot JSON có timestamp.
* `scripts/analyze_macro_delta.py`: So sánh 2 snapshot, tính toán doanh số, xuất báo cáo Markdown và JSON.
* `scripts/automation/scheduler_macro_daemon.py`: Daemon tự chạy ngầm 24/7 theo 3 mốc giờ.
* `scripts/automation/run_macro_snapshot.sh`: Shell runner tích hợp với macOS / Linux crontab.

---

## 8. HƯỚNG DẪN TRIỂN KHAI ĐỘC LẬP & MỞ RỘNG HỆ THỐNG

### 8.1. Khởi Chạy Dự Án Độc Lập
1. Cài đặt môi trường:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
2. Chụp snapshot vĩ mô tức thì:
```bash
python3 scripts/automation/auto_macro_snapshot.py
```
3. So sánh biến động giữa 2 mốc gần nhất:
```bash
python3 scripts/analyze_macro_delta.py
```
4. Kiểm tra tồn kho chính xác của một siêu thị bất kỳ:
```bash
# Theo Apple Store ID
python3 scripts/probe_single_store.py 1472348

# Theo FPT Shop Code
python3 scripts/probe_single_store.py 30841

# Theo địa chỉ / tên đường
python3 scripts/probe_single_store.py "155 Nguyễn Thái Học Vũng Tàu"
```
5. Mở Dashboard báo cáo trực quan:
```bash
open data/reports/fpt_store_inventory_viewer.html
```

### 8.2. Hướng Mở Rộng Tiếp Theo (Roadmap)
* **Mở rộng sang chuỗi Android & Laptop:** Bổ sung danh mục Samsung Galaxy S/Z Series, Xiaomi, Laptop Asus/Dell bằng cách thêm slug vào `config.py`.
* **Cảnh báo Real-Time Telegram / Zalo Webhook:** Khi phát hiện một model "hot" (ví dụ iPhone mới) vừa được restock $> 100$ máy, gửi thông báo đẩy ngay lập tức.
* **Tích hợp Bản đồ Nhiệt Địa lý (Choropleth Map):** Trực quan hóa số lượng máy tồn kho theo từng tỉnh thành / quận huyện trên bản đồ Việt Nam.
