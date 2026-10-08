#!/usr/bin/env python3
"""
Probe Single Product - CellphoneS Intelligence
==============================================
CLI tool to inspect any CellphoneS product URL or slug,
extract full hardware specifications, SMember pricing tiers,
and real-time stock availability in < 200ms.

Usage:
    python probe_product.py iphone-16-pro-max
    python probe_product.py https://cellphones.com.vn/macbook-air-m2-2022-16gb.html
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_DIR))
import config
from src.client import CPSApiClient


def format_vnd(amount) -> str:
    if amount is None or amount == "":
        return "N/A"
    try:
        return f"{int(float(amount)):,}".replace(",", ".") + " ₫"
    except Exception:
        return str(amount)


def probe_product(url_or_slug: str, province_id: int = config.DEFAULT_PROVINCE_ID):
    client = CPSApiClient()
    print(f"\n🚀 [PROBING] Target: {url_or_slug} (Province ID: {province_id})")

    # 1. Fetch Nuxt State
    t0 = sys.platform
    state = client.fetch_product_nuxt_state(url_or_slug)
    if not state:
        print("❌ Could not extract product data. Verify URL/slug.")
        return

    name = state.get("name", "N/A")
    sku = state.get("sku", "N/A")
    price = state.get("price")
    special_price = state.get("special_price")
    stock_state_id = state.get("stock_available_id")
    stock_desc = config.STOCK_AVAILABLE_STATES.get(stock_state_id, f"Trạng thái {stock_state_id}")
    child_ids = state.get("child_product", [])
    prices = state.get("prices", {})

    print("=" * 65)
    print(f"📦 TÊN SẢN PHẨM:   {name}")
    print(f"🏷️  MÃ SKU:         {sku}")
    print(f"🏢 TRẠNG THÁI KHO:  {stock_desc} (Code: {stock_state_id})")
    print("-" * 65)
    print(f"💰 GIÁ NIÊM YẾT:    {format_vnd(price)}")
    print(f"🔥 GIÁ KHUYẾN MÃI:  {format_vnd(special_price)}")

    # SMember Tier Pricing
    if prices:
        print("\n👑 BẢNG GIÁ ĐẶC QUYỀN SMEMBER:")
        special_val = prices.get("special", {}).get("value")
        snew_val = prices.get("snew", {}).get("value")
        smem_val = prices.get("smem", {}).get("value")
        svip_val = prices.get("svip", {}).get("value")

        print(f"   • Khách thường / S-New: {format_vnd(snew_val or special_val)}")
        print(f"   • Hạng S-Mem:           {format_vnd(smem_val)} (Giảm thêm: {format_vnd(prices.get('smem', {}).get('chiet_khau'))})")
        print(f"   • Hạng S-VIP:           {format_vnd(svip_val)} (Giảm thêm: {format_vnd(prices.get('svip', {}).get('chiet_khau'))})")

    # Hardware specs summary
    specs = state.get("specification", {}).get("basic", [])
    if specs:
        print("\n⚙️  THÔNG SỐ KỸ THUẬT NỔI BẬT:")
        for spec in specs[:8]:
            label = spec.get("label")
            val = spec.get("value")
            if label and val:
                # Strip HTML tags
                val_clean = val.replace("<br>", ", ").replace("<b>", "").replace("</b>", "")
                val_clean = " ".join(val_clean.split())[:60]
                print(f"   • {label:25}: {val_clean}")

    # Related Variants (e.g., storage capacities: 256GB, 512GB, 1TB)
    relations = state.get("productData", {}).get("general", {}).get("relation", [])
    all_variant_ids = [state.get("productId")] + [r for r in relations if r != state.get("productId")]
    if all_variant_ids:
        print(f"\n📦 HỌ DÒNG SẢN PHẨM & DUNG LƯỢNG LIÊN KẾT ({len(all_variant_ids)} phiên bản):")
        variants = client.get_products_by_ids(all_variant_ids, province_id=province_id)
        for v in variants:
            v_gen = v.get("general", {})
            v_filt = v.get("filterable", {})
            v_name = v_gen.get("name", "N/A")
            v_special = v_filt.get("special_price")
            v_stock_code = v_filt.get("stock_available_id")
            v_stock_status = "✅ CÒN HÀNG" if v_stock_code == 46 else f"⚠️ TRẠNG THÁI {v_stock_code}"
            print(f"   [{v_stock_status}] {v_name} - {format_vnd(v_special)}")

    # Real-Time Physical Store Stock Probing
    product_id = state.get("productId")
    child_products = state.get("child_product", []) or [product_id]
    print(f"\n🏪 KIỂM TRA TỒN KHO THỰC TẾ TẠI CỬA HÀNG (Real-Time Store Inventory):")
    
    # 1. Nationwide province check
    provinces_map = client.get_instock_provinces(child_products)
    all_instock_provs = set()
    for pid_str, p_list in provinces_map.items():
        for p_item in p_list:
            all_instock_provs.add(p_item.get("province_id"))

    if all_instock_provs:
        print(f"   🌍 Toàn quốc: Có hàng tại {len(all_instock_provs)} tỉnh/thành.")
    else:
        print(f"   ⚠️ Toàn quốc: KHÔNG CÒN HÀNG tại bất kỳ tỉnh thành nào (Hết hàng toàn quốc!).")

    # 2. Local province physical store check
    shops_data = client.get_shops_stock(product_id, province_id=province_id)
    if not shops_data and child_products:
        # Try checking child variants
        for cid in child_products:
            shops_data = client.get_shops_stock(cid, province_id=province_id)
            if shops_data:
                break

    total_shops = sum(len(d.get("shops", [])) for d in shops_data)
    province_name = config.PROVINCE_CODES.get(str(province_id), f"Tỉnh {province_id}")

    if total_shops > 0:
        print(f"   🏬 Tại {province_name}: Có {total_shops} cửa hàng còn hàng sẵn tại quầy.")
        count = 0
        for d in shops_data:
            d_name = d.get("district_name", "")
            for s in d.get("shops", []):
                count += 1
                if count <= 3:
                    print(f"      • [{d_name}] {s.get('address')} (ĐT: {s.get('phone', 'N/A')})")
        if total_shops > 3:
            print(f"      ... và {total_shops - 3} cửa hàng khác.")
    else:
        print(f"   ❌ Tại {province_name}: 0 cửa hàng có sẵn (Thực tế HẾT HÀNG tại quầy).")
        if stock_state_id == 46:
            print(f"   💡 GHI CHÚ: Trạng thái catalog {stock_state_id} là dữ liệu tĩnh/cache; đối chiếu thực tế cửa hàng đã hết hàng hoàn toàn!")

    print("=" * 65)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Probe CellphoneS product availability & pricing.")
    parser.add_argument("target", help="Product URL or slug (e.g. iphone-16-pro-max)")
    parser.add_argument("--province", type=int, default=config.DEFAULT_PROVINCE_ID, help="Province ID (default: 30 - HCM)")
    args = parser.parse_args()

    probe_product(args.target, province_id=args.province)
