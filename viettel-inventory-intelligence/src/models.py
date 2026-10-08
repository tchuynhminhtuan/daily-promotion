"""
Data Models for Viettel Store Inventory Intelligence
=====================================================
Structured data classes representing entities extracted from Viettel Store:
Products, Variants (Rules), Stores, and Inventory Snapshots.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any


@dataclass
class ProvinceInfo:
    province_id: int
    province_code: str
    province_name: str
    erp_province_id: str
    status: bool = True


@dataclass
class StoreStock:
    store_code: str
    province_code: str
    address: str
    status: str = "Còn hàng"


@dataclass
class ProductVariant:
    rule_id: str
    erp_product_id: str
    spec_code: str
    color_name: str
    is_disabled: bool = False
    price: int = 0
    sell_price: int = 0
    amount_in_stock: int = 0
    sale_state: int = 0  # 0: Normal, 1: Out of stock/Register, 2: Pre-order
    discount: int = 0
    stores_in_stock: List[StoreStock] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res["stores_in_stock_count"] = len(self.stores_in_stock)
        return res


@dataclass
class ProductInfo:
    product_id: str
    product_name: str
    category: str = "Điện thoại"
    category_group: str = ""
    url: str = ""
    variants: List[ProductVariant] = field(default_factory=list)
    total_nationwide_stock: int = 0
    has_physical_stock: bool = False
    last_updated: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_id": self.product_id,
            "product_name": self.product_name,
            "category": self.category,
            "category_group": self.category_group,
            "url": self.url,
            "total_nationwide_stock": self.total_nationwide_stock,
            "has_physical_stock": self.has_physical_stock,
            "last_updated": self.last_updated,
            "variants_count": len(self.variants),
            "variants": [v.to_dict() for v in self.variants],
        }
