# ⚡ FPT Retail Inventory Intelligence Engine
> **Microservice Phân Tích & Giám Sát Tồn Kho Thời Gian Thực Mạng Lưới FPT Shop & F.Studio by FPT**

---

## 📌 1. Giới Thiệu Dự Án

`fpt-inventory-intelligence` là một engine dữ liệu độc lập, tự trị (Autonomous Microservice), được thiết kế chuyên biệt để giải mã và khai thác hạ tầng API Gateway thế hệ mới của FPT Retail (`papi.fptshop.com.vn`).

Dự án cung cấp năng lực giám sát **Ground-Truth Inventory** (Tồn kho thực tế tại quầy và kho trung tâm) cho toàn bộ hệ sinh thái sản phẩm Apple (iPhone, iPad, Mac, Apple Watch, AirPods) trên mạng lưới **602 siêu thị FPT Shop & F.Studio by FPT** trên toàn quốc.

### 🎯 Điểm Đặc Biệt Về Thiết Kế Dự Án
- **Thư mục con tự trị (Zero-Coupling):** Nằm gọn trong `daily-promotion/fpt-inventory-intelligence/`, hoàn toàn không phụ thuộc vào code bên ngoài.
- **Sẵn sàng Migration 1-Click:** Khi dự án phát triển hoàn thiện, có thể di chuyển ra repo riêng bất kỳ lúc nào (`mv` hoặc `git init`) mà không cần sửa đổi bất kỳ dòng code hay cấu hình nào.

---

## 🔬 2. Giải Mã Kỹ Thuật Hệ Sinh Thái API Của FPT Retail

| Tiêu Chí So Sánh | Hệ Thống Thế Giới Di Động (MWG) | Hệ Thống FPT Retail (FPT Shop / F.Studio) |
| :--- | :--- | :--- |
| **Kiến Trúc Frontend** | ASP.NET MVC / Web Forms truyền thống | Next.js App Router kết hợp PAPI Gateway |
| **Cơ Chế Phân Kênh** | Tách domain riêng (`topzone.vn` vs `thegioididong.com`) | **Chung Gateway**, phân kênh qua HTTP Header: `order-channel: "1"` (FPT Shop) & `order-channel: "12"` (F.Studio) |
| **API Tồn Kho Quầy** | `POST /aj/Common/CheckStock` (Cookie, `isNewApi: true`, payload phức tạp) | `POST /gw/v1/public/bff-smart-api/order-promising/pick-up-at-shop` (JSON RESTful chuẩn xác) |
| **Đơn Vị Quản Lý (Unit)** | Mặc định theo quy ước nội bộ MWG | Bắt buộc khai báo mã đơn vị `unit: 8` (Quy ước ERP cho "Chiếc/Máy") |
| **Mã Định Danh Địa Lý** | 63 Tỉnh Thành nội bộ MWG | **34 Mã Tỉnh Chuẩn GSO** (Tổng cục Thống kê: `79` HCM, `01` Hà Nội, `48` Đà Nẵng...) |
| **Tọa Độ GPS Cửa Hàng** | Tọa độ phẳng được crawler tính toán | **API trả về sẵn `latitude` và `longitude`** chính xác của từng siêu thị |
| **Địa Chỉ Lịch Sử** | Phải tự map cụm cũ/mới | Có sẵn trường `legacyAddress` / `oldDisplayAddress` ngay trong API |
| **Tốc Độ Quét Toàn Quốc** | ~4.5 - 6.0 giây cho 63 tỉnh | **1.0 - 1.5 giây** cho 34 tỉnh toàn quốc (Nhanh gấp 4 lần) |

---

## 📁 3. Cấu Trúc Thư Mục Độc Lập

```
fpt-inventory-intelligence/
├── README.md                          # Tài liệu kỹ thuật & hướng dẫn vận hành
├── requirements.txt                   # Danh mục thư viện phụ thuộc tối thiểu
├── .gitignore                         # Bộ lọc tệp git cho dự án
├── config.py                          # Cấu hình trung tâm (Endpoints, Headers, Paths)
├── data/
│   ├── master/
│   │   └── fpt_master_stores.json     # Sổ bộ 602 siêu thị FPT Shop & F.Studio có GPS
│   ├── raw/
│   │   ├── fpt_inventory_latest.csv   # Dữ liệu bảng phẳng phục vụ phân tích nhanh
│   │   └── fpt_inventory_deep_latest.json # Snapshot phân tích sâu từng cửa hàng
│   ├── predictions/
│   │   └── fpt_inventory_inference_latest.json # Chỉ số suy luận & rủi ro tồn kho
│   └── reports/
│       └── daily_report_latest.md     # Báo cáo điều hành tự động cập nhật hàng ngày
├── src/
│   ├── pipeline/
│   │   ├── store_master.py            # Quản lý sổ bộ 602 siêu thị & tra cứu GPS
│   │   └── crawler.py                 # Crawler hybrid đa luồng tốc độ cao
│   └── inference/
│       └── daily_inference.py         # Bộ máy phân tích chỉ số rủi ro & báo cáo điều hành
├── scripts/
│   ├── check_store_inventory.py       # Tra cứu nhanh tồn kho theo Shop Code hoặc địa chỉ
│   ├── map_all_fpt_stores.py          # Thống kê phân bổ địa lý & kênh FPT vs F.Studio
│   └── automation/
│       └── run_fpt_pipeline.sh        # Runner 1-click kích hoạt toàn bộ chu trình
└── logs/                              # Nhật ký thực thi
```

---

## 🚀 4. Hướng Dẫn Vận Hành

### Bước 1: Cài đặt môi trường
Dự án sử dụng Python 3.10+ và chỉ yêu cầu các thư viện siêu nhẹ:
```bash
cd fpt-inventory-intelligence
pip install -r requirements.txt
```

### Bước 2: Chạy toàn bộ Pipeline với 1-Click
```bash
./scripts/automation/run_fpt_pipeline.sh
```

### Bước 3: Hoặc chạy từng phân hệ độc lập

1. **Cập nhật danh bạ 602 siêu thị FPT & GPS:**
   ```bash
   python3 src/pipeline/store_master.py
   ```

2. **Chạy Crawler quét tồn kho toàn quốc:**
   ```bash
   python3 src/pipeline/crawler.py --workers 12
   ```

3. **Tổng hợp báo cáo điều hành Markdown:**
   ```bash
   python3 src/inference/daily_inference.py
   ```

4. **Tra cứu siêu thị cụ thể (Ví dụ Shop 30878 hoặc theo đường):**
   ```bash
   python3 scripts/check_store_inventory.py "30878"
   python3 scripts/check_store_inventory.py "Nguyễn Thị Thập"
   ```

5. **Xem thống kê mạng lưới địa lý 602 cửa hàng:**
   ```bash
   python3 scripts/map_all_fpt_stores.py
   ```

---

## 📦 5. Hướng Dẫn Di Chuyển Sang Repository Riêng (Migration Blueprint)

Khi dự án phát triển tốt và muốn tách hoàn toàn ra khỏi `daily-promotion`:

```bash
# Cách 1: Di chuyển thư mục ra đồng cấp
cd /Users/brucehuynh/GitHub
mv daily-promotion/fpt-inventory-intelligence ./fpt-inventory-intelligence
cd fpt-inventory-intelligence

# Khởi tạo Git độc lập
git init
git add .
git commit -m "feat: initial commit for fpt-inventory-intelligence microservice"
git branch -M main
git remote add origin https://github.com/brucehuynh/fpt-inventory-intelligence.git
git push -u origin main
```
*Tất cả đường dẫn trong code sử dụng `PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))`, do đó dự án sẽ hoạt động ngay lập tức 100% mà không phát sinh bất kỳ lỗi đường dẫn nào.*
