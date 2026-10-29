from __future__ import annotations

import asyncio
import logging
import random
import re

import httpx

from .models import Product, StockResult

logger = logging.getLogger(__name__)


class ProductWatcher:
    def __init__(self, timeout_seconds: float) -> None:
        self._client = httpx.AsyncClient(
            timeout=timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": "preorder-sniper/0.1 (personal stock monitor)"},
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def check(self, product: Product) -> StockResult:
        response = await self._client.get(product.url)
        response.raise_for_status()
        available = selector_matches_html(product.available_selector, response.text)
        detail = "availability marker found" if available else "availability marker not found"
        return StockResult(product=product, available=available, detail=detail)


def selector_marker(selector: str) -> str:
    """Derive a conservative HTML marker from an ID or class selector."""
    if selector.startswith("#"):
        return f'id="{selector[1:]}"'
    if selector.startswith("."):
        return selector[1:]
    return selector


def selector_matches_html(selector: str, html: str) -> bool:
    if selector.startswith("#"):
        pattern = rf"""\bid\s*=\s*["']{re.escape(selector[1:])}["']"""
    elif selector.startswith("."):
        class_name = re.escape(selector[1:])
        pattern = rf"""\bclass\s*=\s*["'][^"']*\b{class_name}\b[^"']*["']"""
    elif match := re.fullmatch(r"\[([\w-]+)=['\"]([^'\"]+)['\"]\]", selector):
        attribute, value = match.groups()
        pattern = rf"""\b{re.escape(attribute)}\s*=\s*["']{re.escape(value)}["']"""
    else:
        return selector_marker(selector) in html
    return re.search(pattern, html, flags=re.IGNORECASE) is not None


async def watch_forever(
    watcher: ProductWatcher,
    products: list[Product],
    interval_seconds: float,
    jitter_seconds: float,
    on_available,
) -> None:
    seen_available: set[Product] = set()
    while True:
        results = await asyncio.gather(
            *(watcher.check(product) for product in products), return_exceptions=True
        )
        for product, result in zip(products, results, strict=True):
            if isinstance(result, Exception):
                logger.warning("Check failed for %s: %s", product.retailer, result)
                continue
            if result.available and product not in seen_available:
                seen_available.add(product)
                try:
                    await on_available(result)
                except Exception:
                    logger.exception("Availability callback failed for %s", product.name)
            elif not result.available:
                seen_available.discard(product)
        await asyncio.sleep(interval_seconds + random.uniform(0, jitter_seconds))
