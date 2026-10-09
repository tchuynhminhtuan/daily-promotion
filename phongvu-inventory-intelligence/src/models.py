"""
Data models and typed dataclasses for Phong Vu Inventory Intelligence.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List
from datetime import datetime


@dataclass
class ProductInventory:
    sku: str
    name: str
    brand: str
    price: int
    supplier_retail_price: Optional[int] = None
    discount_percent: Optional[str] = None
    stock_quantity: int = 0
    total_available: Optional[int] = None
    sellable: bool = True
    scarcity_flag: bool = False
    has_gift: bool = False
    canonical_url: str = ""
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StoreInventoryResult:
    store_id: str
    store_name: str
    province: str
    sku: str
    product_name: str
    exact_physical_stock: Optional[int] = None
    in_stock_confirmed: bool = False
    probe_steps: int = 0
    probe_duration_sec: float = 0.0
    notes: str = ""
    probed_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
