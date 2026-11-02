from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from playwright.async_api import async_playwright

from .models import Product, StockResult
from .watcher import BlockedError, ProductWatcher, is_block_page

logger = logging.getLogger(__name__)

BROWSER_RETAILERS = frozenset({"amazon", "bestbuy"})


class BrowserWatcher:
    """Opt-in availability checks through the persistent Playwright profile.

    Retailers in BROWSER_RETAILERS use a real browser page; all others fall back to plain HTTP.
    Anti-bot challenge pages are reported as BlockedError and never worked around.
    """

    def __init__(
        self,
        http_watcher: ProductWatcher,
        browser_data_dir: Path,
        headless: bool = False,
        profile_lock: asyncio.Lock | None = None,
        timeout_seconds: float = 30,
    ) -> None:
        self._http_watcher = http_watcher
        self._browser_data_dir = browser_data_dir
        self._headless = headless
        # Chromium locks a profile per process, so checks and checkouts must not overlap.
        self._profile_lock = profile_lock or asyncio.Lock()
        self._timeout_ms = int(timeout_seconds * 1000)
        self._blocked: set[Product] = set()

    async def close(self) -> None:
        await self._http_watcher.close()

    async def check(self, product: Product) -> StockResult:
        if product.retailer.lower() not in BROWSER_RETAILERS:
            return await self._http_watcher.check(product)
        async with self._profile_lock:
            if product in self._blocked:
                raise BlockedError(f"{product.retailer} checks stopped after an anti-bot challenge page")
            try:
                return await self._check_in_browser(product)
            except BlockedError:
                self._blocked.add(product)
                logger.error(
                    "%s served an anti-bot challenge; browser checks for %s are stopped until restart.",
                    product.retailer,
                    product.name,
                )
                raise

    async def _check_in_browser(self, product: Product) -> StockResult:
        async with async_playwright() as playwright:
            context = await playwright.chromium.launch_persistent_context(
                str(self._browser_data_dir),
                headless=self._headless,
            )
            try:
                page = await context.new_page()
                await page.goto(product.url, wait_until="domcontentloaded", timeout=self._timeout_ms)
                if is_block_page(await page.content()):
                    raise BlockedError(f"{product.retailer} served an anti-bot challenge page")
                available = await page.locator(product.available_selector).count() > 0
            finally:
                await context.close()
        detail = "availability marker found" if available else "availability marker not found"
        return StockResult(product=product, available=available, detail=detail)
