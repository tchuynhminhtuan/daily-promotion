#!/usr/bin/env python3
"""
Probe Inventory & Product Details for Phong Vu SKUs.
Usage:
    python3 probe_sku_inventory.py 260901559
    python3 probe_sku_inventory.py 260900725
"""

import sys
import json
import re
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": "https://phongvu.vn",
    "Referer": "https://phongvu.vn/",
}

# Current build ID - fallback to HTML scrape if build ID expires
BUILD_ID = "ho0A4eRsdUQzuDNcy_KDm"


def probe_sku(sku: str) -> dict:
    url = f"https://phongvu.vn/_next/data/{BUILD_ID}/default/desktop/products/{sku}.json?sku={sku}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            data = res.json()
            return parse_pdp_data(data)
        elif res.status_code == 404:
            # BuildId might have changed, fallback to HTML parsing
            print(f"[*] BuildId might be outdated, falling back to HTML fetch for SKU {sku}...")
            return probe_sku_via_html(sku)
    except Exception as e:
        print(f"[!] Error fetching Next.js data API: {e}")
        return probe_sku_via_html(sku)


def probe_sku_via_html(sku: str) -> dict:
    url = f"https://phongvu.vn/products/{sku}"
    res = requests.get(url, headers=HEADERS, timeout=15)
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', res.text, re.DOTALL)
    if not match:
        raise ValueError(f"Could not locate __NEXT_DATA__ on product page for SKU {sku}")
    data = json.loads(match.group(1))
    return parse_pdp_data(data.get("props", {}))


def parse_pdp_data(props_or_data: dict) -> dict:
    page_props = props_or_data.get("pageProps", props_or_data)
    server_prod = page_props.get("serverProduct", {})
    prod = server_prod.get("product", {})
    prod_info = prod.get("productInfo", {})
    pap = server_prod.get("priceAndPromotions", {})

    total_avail = prod.get("totalAvailable")
    status = prod.get("status", {})
    sellable = status.get("sellable", False)

    stock_display = (
        f"{total_avail} (Chính xác / Khan hiếm)"
        if total_avail is not None
        else ("Dồi dào (>= 10, Không bị giới hạn)" if sellable else "0 (Hết hàng)")
    )

    return {
        "sku": prod_info.get("sku"),
        "name": prod_info.get("name"),
        "brand": prod_info.get("brand", {}).get("name"),
        "sellable": sellable,
        "totalAvailable": total_avail,
        "stock_status_summary": stock_display,
        "price": pap.get("price"),
        "supplierRetailPrice": pap.get("supplierRetailPrice"),
        "discountPercent": pap.get("discountPercent"),
        "hasGift": bool(prod.get("promotions")),
        "canonical": prod_info.get("canonical"),
    }


if __name__ == "__main__":
    sku_target = sys.argv[1] if len(sys.argv) > 1 else "260901559"
    print(f"=== ĐANG TRUY VẤN SKU: {sku_target} TẠI PHONG VŨ ===")
    result = probe_sku(sku_target)
    print(json.dumps(result, indent=2, ensure_ascii=False))
