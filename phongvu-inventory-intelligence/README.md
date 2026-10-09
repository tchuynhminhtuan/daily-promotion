# 🛡️ Phong Vũ Inventory Intelligence

Hệ thống nghiên cứu, bóc tách cấu trúc API ngầm và theo dõi biến động giá & tồn kho của chuỗi bán lẻ **Phong Vũ** (`phongvu.vn`), trực thuộc hệ sinh thái bán lẻ **Teko**.

---

## 📁 Cấu Trúc Thư Mục

```
phongvu-inventory-intelligence/
├── docs/
│   └── PHONGVU_REVERSE_ENGINEERING_PLAYBOOK.md   # Tài liệu chi tiết kiến trúc & API Teko
├── scripts/
│   └── probe_sku_inventory.py                   # Script tra cứu tồn kho & chi tiết SKU
├── data/                                         # Dữ liệu snapshot (nếu có)
├── config.py                                     # Cấu hình endpoint, token, headers
└── README.md                                     # Tài liệu tổng quan
```

---

## ⚡ Các Điểm Phát Hiện Quan Trọng

1. **Kiến Trúc Nền Tảng:** Next.js (SSR) + Hệ sinh thái Microservices Teko (`tekoapis.com`).
2. **Cơ Chế Trả Về Dữ Liệu:**
   - Dữ liệu nạp tĩnh qua thẻ `<script id="__NEXT_DATA__">` trong HTML.
   - Dữ liệu nạp động qua endpoint `/_next/data/{buildId}/default/desktop/products/{sku}.json`.
3. **Cơ Chế Tồn Kho Tổng Của 1 SKU:**
   - **Tầng Danh mục (`stockQuantity`):** Trả về con số chính xác nếu hàng khan hiếm ($1, 2, 5\dots$); bị giới hạn trần ở $1000$ nếu hàng dồi dào.
   - **Tầng Chi tiết sản phẩm (`totalAvailable`):** Trả về số lượng chính xác khi hàng khan hiếm ($\le 5$); trả về `null` kèm `status.sellable = true` khi hàng dồi dào.
   - **Tồn kho vật lý tuyệt đối:** Có thể dò bằng thuật toán tìm kiếm nhị phân $O(\log N)$ qua API Cart Validation của Teko.
