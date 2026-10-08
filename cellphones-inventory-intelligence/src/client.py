"""
CellphoneS API Client
=====================
High-performance HTTP & GraphQL client engineered to query CellphoneS
backend microservices, extract Nuxt SSR hydrated states, and handle
rate limiting with exponential backoff.
"""

import json
import logging
import re
import subprocess
import time
from typing import Any, Dict, List, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import sys
from pathlib import Path

# Add project root to path
PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_DIR))
import config

logger = logging.getLogger("CPSApiClient")


class CPSApiClient:
    def __init__(self, timeout: int = 15, max_retries: int = 3):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(config.HEADERS_COMMON)

        # Configure connection pooling and HTTP retries
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(
            pool_connections=25, pool_maxsize=25, max_retries=retry_strategy
        )
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def query_graphql(
        self,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
        endpoint: str = config.GRAPHQL_V2_ENDPOINT,
    ) -> Dict[str, Any]:
        """Execute a GraphQL query against CellphoneS GraphQL Gateway."""
        payload = {"query": query, "variables": variables or {}}
        for attempt in range(3):
            try:
                response = self.session.post(
                    endpoint,
                    json=payload,
                    timeout=self.timeout,
                )
                if response.status_code in [403, 429]:
                    sleep_time = 2.0 * (attempt + 1)
                    logger.warning(
                        f"WAF Throttling ({response.status_code}). Backing off for {sleep_time}s..."
                    )
                    time.sleep(sleep_time)
                    continue

                response.raise_for_status()
                result = response.json()
                if "errors" in result and result.get("errors"):
                    logger.error(f"GraphQL Errors: {result['errors']}")
                return result
            except requests.RequestException as e:
                logger.error(f"GraphQL request error (attempt {attempt+1}): {e}")
                if attempt == 2:
                    raise
                time.sleep(1.0 * (attempt + 1))
        return {}

    def get_products_by_ids(
        self,
        product_ids: List[Any],
        province_id: int = config.DEFAULT_PROVINCE_ID,
    ) -> List[Dict[str, Any]]:
        """
        Fetch real-time pricing, stock status, and SMember tiers for product IDs.
        Follows CellphoneS Nuxt production inline query structure.
        """
        if not product_ids:
            return []

        str_ids = ['"' + str(pid) + '"' for pid in product_ids]
        ids_formatted = "[" + ", ".join(str_ids) + "]"

        query = f"""
query getProductListByArrayId {{
    products(
        filter: {{
            static: {{
                province_id: {province_id},
                product_id: {ids_formatted},
                stock: {{
                    from: 0
                }}
            }}
        }},
        size: {len(product_ids)}
    ) {{
        general {{
            product_id
            url_path
            name
        }}
        filterable {{
            stock_available_id
            company_stock_id
            is_parent
            price
            prices
            special_price
            thumbnail
            stock
            categories
            promotion_information
        }}
    }}
}}
"""
        result = self.query_graphql(query)
        products = result.get("data", {}).get("products") if result.get("data") else []
        return products or []

    def get_instock_provinces(
        self,
        product_ids: List[Any],
        company_id: int = 12869,
    ) -> Dict[str, List[Dict[str, int]]]:
        """
        Query real-time stock availability across all provinces nationwide.
        Returns a mapping of { product_id: [ {"province_id": 30}, ... ] }.
        If a product is completely out of stock nationwide, it returns an empty list or {}.
        """
        if not product_ids:
            return {}

        ids_formatted = ", ".join(str(pid) for pid in product_ids)
        query = f"""
query InstockProvinces {{
    instock_provinces_by_list(product_ids: [{ids_formatted}], company_id: {company_id})
}}
"""
        result = self.query_graphql(query, endpoint=config.GRAPHQL_V2_ENDPOINT)
        return result.get("data", {}).get("instock_provinces_by_list") or {}

    def get_shops_stock(
        self,
        product_id: Any,
        province_id: int = config.DEFAULT_PROVINCE_ID,
    ) -> List[Dict[str, Any]]:
        """
        Query the exact list of physical stores having physical stock for a specific product.
        Returns list of districts, each containing a list of physical store locations
        (id, address, phone number, coordinates).
        """
        query = f"""
query SHOP_STOCK {{
    shops_stock(productId: {product_id}, provinceId: {province_id}) {{
        district_id
        district_name
        province_id
        province_name
        shops {{
            id
            external_id
            district_id
            province_id
            address
            phone
            near
            google_link
        }}
    }}
}}
"""
        result = self.query_graphql(query, endpoint=config.GRAPHQL_DASHBOARD_ENDPOINT)
        return result.get("data", {}).get("shops_stock") or []



    def fetch_product_nuxt_state(self, url_or_slug: str) -> Optional[Dict[str, Any]]:
        """
        Fetch HTML page and parse the embedded window.__NUXT__ SSR state.
        Returns the entire product schema including general, filterable,
        child_product IDs, and specification details without DOM rendering.
        """
        if not url_or_slug.startswith("http"):
            slug = url_or_slug.rstrip(".html")
            url = f"{config.CPS_HOST}/{slug}.html"
        else:
            url = url_or_slug

        try:
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code == 404:
                logger.info(f"Page not found (404): {url}")
                return None
            response.raise_for_status()
        except requests.RequestException as e:
            logger.warning(f"Request error for {url}: {e}")
            return None

        html = response.text

        # Extract window.__NUXT__
        start_marker = "window.__NUXT__="
        start_idx = html.find(start_marker)
        if start_idx == -1:
            logger.warning(f"window.__NUXT__ not found on {url}")
            return None

        end_idx = html.find("</script>", start_idx)
        if end_idx == -1:
            return None

        nuxt_js = html[start_idx:end_idx]

        # Use Node.js runner to extract the state cleanly
        js_eval_script = f"""
let window = {{}};
{nuxt_js}
const state = window.__NUXT__?.state;
if (!state) {{
    console.log(JSON.stringify({{}}));
}} else {{
    const p = state.product?.productData || {{}};
    console.log(JSON.stringify({{
        "productData": p,
        "productId": state.product?.productId,
        "child_product": p.general?.child_product || [],
        "specification": p.specification || {{}},
        "name": p.general?.name,
        "sku": p.general?.sku,
        "price": p.filterable?.price,
        "special_price": p.filterable?.special_price,
        "prices": p.filterable?.prices,
        "stock": p.filterable?.stock,
        "stock_available_id": p.filterable?.stock_available_id,
        "promotion_information": p.filterable?.promotion_information,
        "company_stock_quantity": p.filterable?.company_stock_quantity
    }}));
}}
"""
        proc = subprocess.run(
            ["node", "-e", js_eval_script],
            capture_output=True,
            text=True,
            check=True,
        )
        output = proc.stdout.strip()
        if output:
            try:
                return json.loads(output)
            except Exception as e:
                logger.error(f"Error parsing evaluated Nuxt state: {e}")
        return None
