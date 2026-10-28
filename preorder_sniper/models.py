from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Product:
    retailer: str
    name: str
    url: str
    available_selector: str
    add_to_cart_selector: str
    checkout_selector: str


@dataclass(frozen=True)
class StockResult:
    product: Product
    available: bool
    detail: str
