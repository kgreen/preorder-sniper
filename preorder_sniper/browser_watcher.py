from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import httpx
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from .models import Product, StockResult
from .watcher import BlockedError, ProductWatcher, is_block_page

logger = logging.getLogger(__name__)

BROWSER_RETAILERS = frozenset({"amazon", "bestbuy"})


class BrowserBusyError(RuntimeError):
    """The shared browser profile is in use (for example by checkout); this poll was skipped."""


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
        render_timeout_seconds: float = 10,
    ) -> None:
        self._http_watcher = http_watcher
        self._browser_data_dir = browser_data_dir
        self._headless = headless
        # Chromium locks a profile per process, so checks and checkout must not overlap.
        self._profile_lock = profile_lock or asyncio.Lock()
        self._timeout_ms = int(timeout_seconds * 1000)
        self._render_timeout_ms = int(render_timeout_seconds * 1000)
        self._blocked: set[Product] = set()

    async def close(self) -> None:
        await self._http_watcher.close()

    async def check(self, product: Product) -> StockResult:
        if product.retailer.lower() not in BROWSER_RETAILERS:
            return await self._http_watcher.check(product)
        if product in self._blocked:
            raise BlockedError(f"{product.retailer} checks stopped after an anti-bot challenge page")
        # Never wait on the profile: a long checkout review would stall unrelated monitoring.
        if self._profile_lock.locked():
            raise BrowserBusyError(f"browser profile is busy; skipped {product.name} this poll")
        async with self._profile_lock:
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
                response = await page.goto(product.url, wait_until="domcontentloaded", timeout=self._timeout_ms)
                self._raise_if_blocked(product, await page.content())
                if response is not None and response.status >= 400:
                    raise _status_error(product.url, response.status, response.headers)
                try:
                    await page.locator(product.available_selector).first.wait_for(
                        state="attached", timeout=self._render_timeout_ms
                    )
                    available = True
                except PlaywrightTimeoutError:
                    available = False
                self._raise_if_blocked(product, await page.content())
            finally:
                await context.close()
        detail = "availability marker found" if available else "availability marker not found"
        return StockResult(product=product, available=available, detail=detail)

    @staticmethod
    def _raise_if_blocked(product: Product, html: str) -> None:
        if is_block_page(html):
            raise BlockedError(f"{product.retailer} served an anti-bot challenge page")


def _status_error(url: str, status: int, headers: dict[str, str]) -> httpx.HTTPStatusError:
    """Mirror httpx's error so watch_forever's existing 429/Retry-After backoff applies."""
    request = httpx.Request("GET", url)
    return httpx.HTTPStatusError(
        f"HTTP {status} for {url}",
        request=request,
        response=httpx.Response(status, headers=headers, request=request),
    )
