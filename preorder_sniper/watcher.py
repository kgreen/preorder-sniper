from __future__ import annotations

import asyncio
import logging
import random
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

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
        if is_block_page(response.text):
            raise BlockedError(f"{product.retailer} served an anti-bot challenge page")
        available = selector_matches_html(product.available_selector, response.text)
        detail = "availability marker found" if available else "availability marker not found"
        return StockResult(product=product, available=available, detail=detail)


class BlockedError(RuntimeError):
    """The retailer returned an anti-bot challenge instead of the product page."""


BLOCK_PAGE_MARKERS = ("/errors/validatecaptcha",)


def is_block_page(html: str) -> bool:
    lowered = html.lower()
    return any(marker in lowered for marker in BLOCK_PAGE_MARKERS)


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


def rate_limit_delay(error: Exception, interval_seconds: float) -> float:
    """Return a backoff delay in seconds for an HTTP 429 error, else 0."""
    if not isinstance(error, httpx.HTTPStatusError) or error.response.status_code != 429:
        return 0.0
    retry_after = error.response.headers.get("Retry-After", "")
    try:
        delay = float(retry_after)
    except ValueError:
        try:
            delay = (parsedate_to_datetime(retry_after) - datetime.now(timezone.utc)).total_seconds()
        except (TypeError, ValueError):
            delay = interval_seconds * 6
    return min(max(delay, interval_seconds), 600.0)


async def watch_forever(
    watcher: ProductWatcher,
    products: list[Product],
    interval_seconds: float,
    jitter_seconds: float,
    on_available,
) -> None:
    seen_available: set[Product] = set()
    backoff_until: dict[Product, float] = {}
    while True:
        now = time.monotonic()
        due = [p for p in products if backoff_until.get(p, 0) <= now]
        results = await asyncio.gather(*(watcher.check(p) for p in due), return_exceptions=True)
        for product, result in zip(due, results, strict=True):
            if isinstance(result, Exception):
                logger.warning("Check failed for %s: %s", product.retailer, result)
                delay = rate_limit_delay(result, interval_seconds)
                if delay:
                    backoff_until[product] = time.monotonic() + delay
                    logger.warning("Backing off %s for %.0fs after HTTP 429", product.name, delay)
                continue
            backoff_until.pop(product, None)
            if result.available:
                if product in seen_available:
                    continue
                try:
                    await on_available(result)
                except Exception:
                    logger.exception("Availability callback failed for %s; retrying on the next poll.", product.name)
                    continue
                seen_available.add(product)
            else:
                seen_available.discard(product)
        await asyncio.sleep(interval_seconds + random.uniform(0, jitter_seconds))
