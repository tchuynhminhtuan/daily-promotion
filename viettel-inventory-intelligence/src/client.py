"""
Viettel Store API Client
========================
High-performance HTTP client engineered to query Viettel Store's multi-layered
backend architecture: ASMX JSON-RPC, AjaxAction handlers, Customer-Service
Microservices, and Async Server-Side Components.
"""

import json
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_DIR))
import config
from src.models import ProductInfo, ProductVariant, StoreStock, ProvinceInfo

logger = logging.getLogger("ViettelStoreClient")


class ViettelStoreClient:
    """Client for querying Viettel Store backend APIs."""

    def __init__(self, timeout: int = 12, max_retries: int = 3):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(config.HEADERS_AJAX)

        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(
            pool_connections=25, pool_maxsize=25, max_retries=retry_strategy
        )
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _post(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Tuple[int, str]:
        """
        Robust POST dispatcher: First tries requests Session, but automatically
        falls back to HTTP/2 curl subprocess if Akamai returns 403 or blocks TLS.
        """
        hdrs = {**config.HEADERS_AJAX, **(headers or {})}
        try:
            if json_data is not None:
                resp = self.session.post(url, json=json_data, headers=hdrs, timeout=self.timeout)
            else:
                resp = self.session.post(url, data=data, headers=hdrs, timeout=self.timeout)

            if resp.status_code != 403:
                return resp.status_code, resp.text
        except Exception as e:
            logger.debug(f"Session POST failed, trying curl fallback: {e}")

        # Fallback to curl HTTP/2
        import subprocess
        import urllib.parse
        cmd = ["curl", "-s", "-w", "\n%{http_code}", "-X", "POST", url]
        for k, v in hdrs.items():
            cmd.extend(["-H", f"{k}: {v}"])
        if json_data is not None:
            cmd.extend(["-H", "Content-Type: application/json; charset=utf-8", "-d", json.dumps(json_data)])
        elif data is not None:
            body = urllib.parse.urlencode(data)
            cmd.extend(["-d", body])

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout)
            out = res.stdout
            lines = out.rsplit("\n", 1)
            if len(lines) == 2:
                body_text, status_str = lines[0], lines[1]
                status_code = int(status_str) if status_str.isdigit() else 200
                return status_code, body_text
            return 200, out
        except Exception as e:
            logger.error(f"Curl fallback execution failed: {e}")
            return 500, ""

    # =========================================================================
    # 1. Master Data & Microservice Gateway
    # =========================================================================
    def get_master_provinces(self) -> List[ProvinceInfo]:
        """Fetch standardized list of provinces from Customer Microservice Gateway."""
        url = config.SYS_AJAX_ENDPOINT
        data = {
            "a": "customer-service",
            "methodName": "POST",
            "path": "/profile/v1/province/load",
            "requestBody": "{}",
        }
        try:
            status, raw_text = self._post(url, data=data)
            if status != 200:
                logger.error(f"Failed to fetch provinces, HTTP {status}")
                return []

            # Response structure: { stt: 1, msg: 'OK', data: '{"timeEpoch":..., "result":{"provinces":[...]}}' }
            raw_text = raw_text.strip()
            data_json_match = re.search(r"data:\s*'({.+})'\s*}", raw_text)
            if data_json_match:
                inner_json_str = data_json_match.group(1).replace("\\'", "'")
                payload = json.loads(inner_json_str)
            else:
                clean_json = re.sub(r"([{,])\s*([a-zA-Z0-9_]+)\s*:", r'\1"\2":', raw_text)
                clean_json = clean_json.replace("'", '"')
                parsed = json.loads(clean_json)
                payload = json.loads(parsed.get("data", "{}"))

            provinces = []
            for item in payload.get("result", {}).get("provinces", []):
                provinces.append(
                    ProvinceInfo(
                        province_id=item.get("provinceId"),
                        province_code=item.get("provinceCode", ""),
                        province_name=item.get("provinceName", ""),
                        erp_province_id=str(item.get("erpProvinceId", "")),
                        status=item.get("status", True),
                    )
                )
            return provinces
        except Exception as e:
            logger.error(f"Error fetching provinces from Viettel gateway: {e}")
            return []

    # =========================================================================
    # 2. Product Variants & Rules (Tầng 3)
    # =========================================================================
    def get_product_rules(self, product_id: str) -> List[ProductVariant]:
        """
        Bóc tách danh sách biến thể màu sắc, Rule_ID và Erp_Product_ID của sản phẩm.
        """
        url = config.AJAX_ACTION_ENDPOINT
        data = {
            "action": "get-list-rule-by-product",
            "productId": str(product_id),
        }
        headers = {
            "Referer": f"{config.VT_HOST}/dien-thoai/-pid{product_id}.html",
        }
        try:
            status, html = self._post(url, data=data, headers=headers)
            if status != 200:
                return []

            soup = BeautifulSoup(html, "html.parser")
            variants = []

            for li in soup.find_all("li"):
                label = li.find("label", class_=re.compile(r"color-check"))
                if not label:
                    continue

                rule_id = label.get("id", "").strip()
                color_name = label.get("title", "").strip()
                is_disabled = "disabled" in label.attrs or "opacity: 0.4" in label.get("style", "")

                input_tag = li.find("input", type="radio")
                erp_product_id = ""
                spec_code = ""
                if input_tag:
                    erp_product_id = str(input_tag.get("data-erp", "")).strip()
                    spec_code = str(input_tag.get("data-spec", "")).strip()

                if not color_name and li.find(class_="txt-color"):
                    color_name = li.find(class_="txt-color").get_text(strip=True)

                if rule_id or erp_product_id:
                    variants.append(
                        ProductVariant(
                            rule_id=rule_id,
                            erp_product_id=erp_product_id,
                            spec_code=spec_code,
                            color_name=color_name,
                            is_disabled=is_disabled,
                        )
                    )

            return variants
        except Exception as e:
            logger.error(f"Error fetching rules for product {product_id}: {e}")
            return []

    # =========================================================================
    # 3. ASMX JSON-RPC Pricing & Stock Probing (Tầng 1)
    # =========================================================================
    def get_price_and_stock(
        self, product_id: str, rule_id: str = ""
    ) -> Dict[str, Any]:
        """
        Query ASMX Web Service for real-time ERP pricing and nationwide stock count.
        """
        url = config.ASMX_GET_PRICE_STOCK
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Referer": f"{config.VT_HOST}/dien-thoai/-pid{product_id}.html",
        }
        payload = {"id": rule_id, "pid": str(product_id)}

        try:
            status, text = self._post(url, json_data=payload, headers=headers)
            if status != 200:
                return {}

            res_obj = json.loads(text)
            data = res_obj.get("d", {}).get("data", {})
            if not data:
                return {}

            price = int(float(data.get("Price", 0) or 0))
            sell_price = int(float(data.get("SellPrice", 0) or 0))
            amount_in_stock = int(float(data.get("AmounInstock", 0) or 0))
            discount = int(float(data.get("Discount", 0) or 0))
            sale_state = int(float(data.get("SaleState", 0) or 0))
            erp_product_id = str(data.get("Erp_Product_ID", "")).strip()

            return {
                "price": price,
                "sell_price": sell_price,
                "amount_in_stock": amount_in_stock,
                "discount": discount,
                "sale_state": sale_state,
                "erp_product_id": erp_product_id,
            }
        except Exception as e:
            logger.error(
                f"Error fetching ASMX price/stock for PID {product_id}, Rule {rule_id}: {e}"
            )
            return {}

    # =========================================================================
    # 4. Store-Level Inventory Engine (Tầng 2)
    # =========================================================================
    def get_store_inventory(
        self, erp_product_id: str, province_id: str = "-1"
    ) -> List[StoreStock]:
        """
        Query all stores/supermarkets holding physical stock for this ERP product.
        province_id="-1" probes nationwide across all 63 provinces.
        """
        if not erp_product_id:
            return []

        url = config.AJAX_ACTION_ENDPOINT
        data = {
            "action": "get-markets-for-erp-checktonkho",
            "provinceId": str(province_id),
            "districtId": "0",
            "productId": str(erp_product_id),
            "specCode": str(erp_product_id),
        }

        try:
            status, html = self._post(url, data=data)
            if status != 200 or "Không tìm thấy Siêu Thị còn hàng" in html:
                return []

            soup = BeautifulSoup(html, "html.parser")
            stores = []

            for div in soup.find_all("div", class_="item"):
                if "hidden" in div.get("class", []):
                    continue

                text = div.get_text(" ", strip=True)
                if not text or "Còn hàng" not in text:
                    continue

                match = re.search(
                    r"^([A-Z0-9]+)\s*-\s*([A-Z0-9]+)\s*,\s*[^,]+,\s*(.+?)\s*-\s*Còn hàng",
                    text,
                )
                if match:
                    store_code = match.group(1).strip()
                    province_code = match.group(2).strip()
                    address = match.group(3).strip()
                else:
                    parts = text.split("-")
                    store_code = parts[0].strip() if len(parts) > 0 else ""
                    province_code = ""
                    address = parts[1].strip() if len(parts) > 1 else text

                stores.append(
                    StoreStock(
                        store_code=store_code,
                        province_code=province_code,
                        address=address,
                        status="Còn hàng",
                    )
                )

            return stores
        except Exception as e:
            logger.error(
                f"Error checking store inventory for ERP PID {erp_product_id}: {e}"
            )
            return []

    # =========================================================================
    # =========================================================================
    # 5. Catalog Discovery & Dynamic Pagination (Tầng 4)
    # =========================================================================
    def get_catalog_page(
        self,
        cat_id: str = "010001",
        man_id: str = "1",
        page: int = 1,
        page_size: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Extract catalog products for a category & brand via Async Component SSR.
        Parses direct HTML product markup (data-id, data-name, data-price, href).
        """
        url = config.USER_CONTROL_ASYNC_ENDPOINT
        data = {
            "path": "ProductList5Col2026",
            "CatID": str(cat_id),
            "ManID": str(man_id),
            "PageSize": page_size,
            "CurrentPage": page,
        }

        try:
            status, html = self._post(url, data=data)
            if status != 200:
                return []

            soup = BeautifulSoup(html, "html.parser")
            products = []
            seen_pids = set()

            links = soup.find_all("a", href=re.compile(r"-pid\d+\.html"))
            for a in links:
                pid = str(a.get("data-id") or "").strip()
                href = a.get("href", "").strip()
                if not pid:
                    pid_match = re.search(r"-pid(\d+)\.html", href)
                    pid = pid_match.group(1) if pid_match else ""

                if not pid or pid in seen_pids:
                    continue

                seen_pids.add(pid)

                # Extract product name
                name = str(a.get("data-name") or "").strip()
                if not name:
                    h3 = a.find("h3")
                    if h3:
                        name = h3.get_text(strip=True)
                    else:
                        title_elem = a.find(class_=re.compile(r"name|title"))
                        name = title_elem.get_text(strip=True) if title_elem else a.get_text(" ", strip=True)

                # Extract price
                price = 0
                price_attr = a.get("data-price")
                if price_attr:
                    try:
                        price = int(float(price_attr))
                    except ValueError:
                        pass
                if not price:
                    price_elem = a.find(class_=re.compile(r"price|new-price"))
                    if price_elem:
                        price = int(re.sub(r"[^\d]", "", price_elem.get_text(strip=True)) or 0)

                full_url = href if href.startswith("http") else f"{config.VT_HOST}{href}"

                products.append(
                    {
                        "product_id": pid,
                        "product_name": name,
                        "price": price,
                        "url": full_url,
                        "brand": "Apple" if str(man_id) == "1" else "",
                    }
                )

            return products
        except Exception as e:
            logger.error(f"Error fetching catalog page {page} for cat {cat_id}: {e}")
            return []

    def discover_all_apple_products(self) -> List[Dict[str, Any]]:
        """
        Crawl the entire Apple ecosystem on Viettel Store:
        - iPhone (010001)
        - iPad (010003)
        - Apple Watch (010005023)
        - AirPods (010005005)
        - Apple Pencil & Phụ kiện khác (010005019)
        - Sạc Cáp Apple (010005014)
        - Ốp Lưng Apple (010005012)
        Returns a deduplicated list of all Apple catalog items with category tags.
        """
        all_items: List[Dict[str, Any]] = []
        seen_pids = set()

        for group_name, cat_id in config.APPLE_ECOSYSTEM_CATEGORIES.items():
            page = 1
            group_count = 0
            while True:
                items = self.get_catalog_page(cat_id=cat_id, man_id="1", page=page, page_size=50)
                if not items:
                    break

                new_items_in_page = 0
                for item in items:
                    pid = item["product_id"]
                    if pid not in seen_pids:
                        seen_pids.add(pid)
                        item["category_group"] = group_name
                        item["category"] = group_name
                        all_items.append(item)
                        group_count += 1
                        new_items_in_page += 1

                if new_items_in_page == 0 or len(items) < 50:
                    break
                page += 1

            logger.info(f"Discovered {group_count} Apple items in group '{group_name}' (CatID {cat_id})")

        return all_items

    # =========================================================================
    # 6. Ancillary Product & Promotional Data
    # =========================================================================
    def get_ancillary_product_info(
        self, product_id: str, erp_product_id: str = ""
    ) -> Dict[str, Any]:
        """
        Extract rich auxiliary commercial & marketing metadata:
        - Payment promotions & bank discounts (Kredivo, TPBank EVO, MB, Vikki)
        - Cross-sell bundles (Flycam DJI, Rokid AI glasses, chargers)
        - Viettel++ loyalty coupon program
        - Trade-in valuation support
        """
        url = config.AJAX_ACTION_ENDPOINT
        res: Dict[str, Any] = {
            "payment_promotions": [],
            "accessory_bundles": [],
            "viettel_plus_available": False,
            "trade_in_available": False,
        }

        # 1. Payment Promotions
        try:
            status, text = self._post(
                url, data={"action": "get-payment-promotion", "productId": str(product_id)}
            )
            if status == 200:
                soup = BeautifulSoup(text, "html.parser")
                for promo in soup.find_all(class_=re.compile(r"payment-promo|item")):
                    t = promo.get_text(" ", strip=True)
                    if t and t not in res["payment_promotions"]:
                        res["payment_promotions"].append(t)
        except Exception as e:
            logger.debug(f"Error fetching payment promo for {product_id}: {e}")

        # 2. Accessory cross-sell
        if erp_product_id:
            try:
                status, text = self._post(
                    url,
                    data={"action": "get-list-product-buy-more-erp", "productId": str(product_id), "erpId": str(erp_product_id)},
                )
                if status == 200:
                    soup = BeautifulSoup(text, "html.parser")
                    for it in soup.find_all(class_=re.compile(r"item|prod")):
                        t = it.get_text(" ", strip=True)
                        if "Giảm" in t or "Mua kèm" in t:
                            res["accessory_bundles"].append(t[:120])
            except Exception as e:
                logger.debug(f"Error fetching cross-sell for {product_id}: {e}")

        # 3. Viettel++ Loyalty
        try:
            status, text = self._post(
                url, data={"action": "load-promotion-vtplus", "productId": str(product_id)}
            )
            if status == 200 and "Viettel++" in text:
                res["viettel_plus_available"] = True
        except Exception:
            pass

        # 4. Trade-in
        try:
            status, text = self._post(
                url, data={"action": "load-button-tradedin", "productId": str(product_id)}
            )
            if status == 200 and "THU CŨ ĐỔI MỚI" in text:
                res["trade_in_available"] = True
        except Exception:
            pass

        return res

    # =========================================================================
    # 7. Comprehensive Deep Product Probe
    # =========================================================================
    def probe_product(
        self,
        product_id: str,
        product_name: str = "",
        category_group: str = "",
        url: str = "",
        include_stores: bool = True,
    ) -> ProductInfo:
        """
        Deep probe a single product:
        - Extract all color variants (Rules)
        - Query exact ERP pricing & nationwide stock count for each variant
        - Probe store breakdown for in-stock variants
        """
        variants = self.get_product_rules(product_id)

        # If no variants discovered via rules, fallback to default variant query
        if not variants:
            default_stock = self.get_price_and_stock(product_id, rule_id="")
            if default_stock:
                variants = [
                    ProductVariant(
                        rule_id="",
                        erp_product_id=default_stock.get("erp_product_id", ""),
                        spec_code="DEFAULT",
                        color_name="Mặc định",
                        price=default_stock.get("price", 0),
                        sell_price=default_stock.get("sell_price", 0),
                        amount_in_stock=default_stock.get("amount_in_stock", 0),
                        sale_state=default_stock.get("sale_state", 0),
                        discount=default_stock.get("discount", 0),
                    )
                ]

        total_stock = 0
        has_physical_stock = False

        for v in variants:
            stock_data = self.get_price_and_stock(product_id, rule_id=v.rule_id)
            if stock_data:
                v.price = stock_data.get("price", v.price)
                v.sell_price = stock_data.get("sell_price", v.sell_price)
                v.amount_in_stock = stock_data.get("amount_in_stock", 0)
                v.discount = stock_data.get("discount", 0)
                v.sale_state = stock_data.get("sale_state", 0)
                if not v.erp_product_id and stock_data.get("erp_product_id"):
                    v.erp_product_id = stock_data.get("erp_product_id")

            total_stock += v.amount_in_stock
            if v.amount_in_stock > 0:
                has_physical_stock = True

            # If stores requested and variant has stock, probe store details
            if include_stores and v.amount_in_stock > 0 and v.erp_product_id:
                v.stores_in_stock = self.get_store_inventory(
                    v.erp_product_id, province_id="-1"
                )

        final_url = url or f"{config.VT_HOST}/dien-thoai/-pid{product_id}.html"

        info = ProductInfo(
            product_id=str(product_id),
            product_name=product_name,
            category=category_group or "Apple",
            category_group=category_group,
            url=final_url,
            variants=variants,
            total_nationwide_stock=total_stock,
            has_physical_stock=has_physical_stock,
            last_updated=time.strftime("%Y-%m-%d %H:%M:%S"),
        )
        return info
