"""
High-Speed Catalog Crawler for Phong Vu Categories.
Extracts all SKUs, prices, promotions, and total stockQuantity.
"""

import os
import sys
import json
import re
import time
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import (
    PHONGVU_BASE_URL,
    CURRENT_BUILD_ID,
    HEADERS_COMMON,
)


class PhongVuCatalogCrawler:
    def __init__(self, build_id: str = CURRENT_BUILD_ID):
        self.build_id = build_id
        self.session = requests.Session()
        self.session.headers.update(HEADERS_COMMON)

    def update_build_id_from_html(self, slug: str = "san-pham-apple") -> str:
        """Fetches HTML page to auto-detect current Next.js buildId if expired."""
        url = f"{PHONGVU_BASE_URL}/c/{slug}"
        try:
            r = self.session.get(url, timeout=12)
            match = re.search(r'"buildId":"([^"]+)"', r.text)
            if match:
                self.build_id = match.group(1)
                print(f"[i] Updated Next.js BuildId: {self.build_id}")
                return self.build_id
        except Exception as e:
            print(f"[!] Warning: Could not detect buildId from HTML: {e}")
        return self.build_id

    def fetch_page(self, slug: str, page: int = 1) -> Optional[Dict[str, Any]]:
        """Fetches 1 page via Next.js Data API (pure JSON) with fallback."""
        url = (
            f"{PHONGVU_BASE_URL}/_next/data/{self.build_id}/default/desktop/c/{slug}.json"
            f"?slug={slug}" + (f"&page={page}" if page > 1 else "")
        )
        try:
            r = self.session.get(url, timeout=12)
            if r.status_code == 200:
                data = r.json()
                return data.get("pageProps", {})
            elif r.status_code == 404:
                # Refresh build ID and retry once
                self.update_build_id_from_html(slug)
                url = (
                    f"{PHONGVU_BASE_URL}/_next/data/{self.build_id}/default/desktop/c/{slug}.json"
                    f"?slug={slug}" + (f"&page={page}" if page > 1 else "")
                )
                r = self.session.get(url, timeout=12)
                if r.status_code == 200:
                    return r.json().get("pageProps", {})
        except Exception as e:
            print(f"[!] Error fetching page {page} for category {slug}: {e}")
        return None

    def crawl_category(
        self,
        slug: str = "san-pham-apple",
        max_pages: Optional[int] = None,
        max_workers: int = 4
    ) -> List[Dict[str, Any]]:
        """Crawls all products in a given category."""
        print(f"\n🚀 Khởi động quét danh mục Phong Vũ: '{slug}'")
        first_page = self.fetch_page(slug, page=1)
        if not first_page:
            print(f"❌ Không lấy được dữ liệu trang 1 cho danh mục: '{slug}'")
            return []

        server_pagination = first_page.get("serverPagination", {})
        total_items = server_pagination.get("totalItems", 0)
        total_pages = server_pagination.get("totalPages", 1)

        print(f"📦 Tổng sản phẩm trong danh mục: {total_items:,} (Tổng số trang: {total_pages})")

        pages_to_fetch = total_pages
        if max_pages and max_pages < total_pages:
            pages_to_fetch = max_pages
            print(f"⚙️ Giới hạn quét: {pages_to_fetch} trang đầu")

        all_products: List[Dict[str, Any]] = []

        # Parse trang 1 đã lấy
        first_products = first_page.get("serverProducts", [])
        all_products.extend([self._format_product(p) for p in first_products])
        print(f"  • Trang 1/{pages_to_fetch}: Lấy được {len(first_products)} SKU")

        if pages_to_fetch > 1:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_page = {
                    executor.submit(self.fetch_page, slug, p): p
                    for p in range(2, pages_to_fetch + 1)
                }
                for future in as_completed(future_to_page):
                    p_num = future_to_page[future]
                    try:
                        res = future.result()
                        if res:
                            prods = res.get("serverProducts", [])
                            formatted = [self._format_product(p) for p in prods]
                            all_products.extend(formatted)
                            print(f"  • Trang {p_num}/{pages_to_fetch}: Lấy được {len(formatted)} SKU")
                    except Exception as exc:
                        print(f"  ❌ Lỗi khi tải trang {p_num}: {exc}")

        # Sắp xếp lại theo SKU hoặc tên
        all_products.sort(key=lambda x: x.get("sku", ""))
        print(f"\n✅ Hoàn tất! Tổng cộng thu thập được {len(all_products)} SKU từ danh mục '{slug}'")
        return all_products

    def _format_product(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Chuẩn hóa dữ liệu sản phẩm."""
        price_obj = raw.get("price", {})
        stock_qty = raw.get("stockQuantity", 0)
        scarcity = 0 < stock_qty <= 5

        return {
            "sku": raw.get("sku"),
            "seller_sku": raw.get("sellerSku"),
            "name": raw.get("name"),
            "brand": raw.get("brand", {}).get("name", "Unknown"),
            "price": price_obj.get("latestPrice", 0),
            "supplier_retail_price": price_obj.get("supplierRetailPrice", 0),
            "discount_amount": price_obj.get("discountAmount", 0),
            "discount_percent": price_obj.get("discountPercent", "0%"),
            "stock_quantity": stock_qty,
            "scarcity_flag": scarcity,
            "stock_status": (
                f"Sắp hết (Chính xác {stock_qty} chiếc)"
                if scarcity
                else ("Dồi dào (>= 10)" if stock_qty >= 1000 else f"Còn {stock_qty}")
            ),
            "has_gift": raw.get("hasGift", False),
            "select_promotion_id": raw.get("selectPromotionId"),
            "categories": [c.get("name") for c in raw.get("categories", [])],
            "canonical": raw.get("link", {}).get("as", {}).get("pathname", ""),
            "image_url": raw.get("imageUrl", ""),
        }
