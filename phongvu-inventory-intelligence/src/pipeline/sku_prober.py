"""
Single SKU Deep Prober for Phong Vu.
Extracts product details, price, promotions, totalAvailable, and sellable status.
"""

import os
import sys
import json
import re
from typing import Dict, Any, Optional
import requests

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import (
    PHONGVU_BASE_URL,
    CURRENT_BUILD_ID,
    HEADERS_COMMON,
)


class PhongVuSkuProber:
    def __init__(self, build_id: str = CURRENT_BUILD_ID):
        self.build_id = build_id
        self.session = requests.Session()
        self.session.headers.update(HEADERS_COMMON)

    def probe_sku(self, sku: str) -> Optional[Dict[str, Any]]:
        """Probes a single SKU by Next.js Data API with fallback to HTML."""
        url = f"{PHONGVU_BASE_URL}/_next/data/{self.build_id}/default/desktop/products/{sku}.json?sku={sku}"
        try:
            r = self.session.get(url, timeout=12)
            if r.status_code == 200:
                return self._parse_pdp_payload(r.json().get("pageProps", {}))
            elif r.status_code == 404:
                return self._probe_sku_via_html(sku)
        except Exception as e:
            print(f"[!] Warning: Data API error for SKU {sku}: {e}, falling back to HTML")
            return self._probe_sku_via_html(sku)
        return None

    def _probe_sku_via_html(self, sku: str) -> Optional[Dict[str, Any]]:
        url = f"{PHONGVU_BASE_URL}/products/{sku}"
        try:
            r = self.session.get(url, timeout=15)
            match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
                # Update buildId if available
                if "buildId" in data:
                    self.build_id = data["buildId"]
                return self._parse_pdp_payload(data.get("props", {}).get("pageProps", {}))
        except Exception as e:
            print(f"❌ Failed to probe SKU {sku} via HTML: {e}")
        return None

    def _parse_pdp_payload(self, page_props: Dict[str, Any]) -> Dict[str, Any]:
        server_product = page_props.get("serverProduct", {})
        prod = server_product.get("product", {})
        prod_info = prod.get("productInfo", {})
        pap = server_product.get("priceAndPromotions", {})

        total_avail = prod.get("totalAvailable")
        status = prod.get("status", {})
        sellable = status.get("sellable", True)

        scarcity = total_avail is not None and total_avail <= 5

        stock_desc = (
            f"Còn chính xác {total_avail} máy (Khan hiếm)"
            if total_avail is not None
            else ("Dồi dào (>= 10 máy)" if sellable else "0 máy (Hết hàng)")
        )

        return {
            "sku": prod_info.get("sku"),
            "name": prod_info.get("name"),
            "brand": prod_info.get("brand", {}).get("name", "Unknown"),
            "sellable": sellable,
            "total_available": total_avail,
            "scarcity_flag": scarcity,
            "stock_status_summary": stock_desc,
            "price": pap.get("price", 0),
            "supplier_retail_price": pap.get("supplierRetailPrice", 0),
            "discount_percent": pap.get("discountPercent", "0%"),
            "promotions": pap.get("promotions", []),
            "canonical": prod_info.get("canonical", ""),
            "image_url": prod_info.get("imageUrl", ""),
        }
