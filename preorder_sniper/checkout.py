from __future__ import annotations

import logging
from pathlib import Path

from playwright.async_api import async_playwright

from .models import Product

logger = logging.getLogger(__name__)


class AssistedCheckout:
    def __init__(self, browser_data_dir: Path, headless: bool = False) -> None:
        self._browser_data_dir = browser_data_dir
        self._headless = headless

    async def run(self, product: Product) -> None:
        """Attempt add-to-cart then pause at checkout for manual review; never submit an order."""
        async with async_playwright() as playwright:
            context = await playwright.chromium.launch_persistent_context(
                str(self._browser_data_dir),
                headless=self._headless,
            )
            page = await context.new_page()
            try:
                await page.goto(product.url, wait_until="domcontentloaded")

                await self._click_if_present(page, product.add_to_cart_selector, "add to cart")
                await self._click_if_present(page, product.checkout_selector, "checkout")

                logger.warning(
                    "Checkout reached for %s at %s. Pausing for manual review before any order submission.",
                    product.name,
                    product.url,
                )
                await self._pause_for_manual_review(page)
            finally:
                await context.close()

    async def _click_if_present(self, page, selector: str, action_name: str) -> None:
        locator = page.locator(selector)
        try:
            await locator.click(timeout=10_000)
        except TimeoutError:
            logger.warning("No matching %s selector was found for %s.", action_name, selector)
            raise

    async def _pause_for_manual_review(self, page) -> None:
        await page.bring_to_front()
        logger.warning(
            "Manual approval required before final purchase submission."
            " The browser is intentionally left at checkout and no submit action is triggered."
        )
        await page.wait_for_timeout(600_000)

    async def open_login_pages(self, products: list[Product]) -> None:
        """Open retailer pages in the persistent profile for a manual sign-in."""
        async with async_playwright() as playwright:
            context = await playwright.chromium.launch_persistent_context(
                str(self._browser_data_dir),
                headless=False,
            )
            try:
                for product in products:
                    page = await context.new_page()
                    await page.goto(product.url, wait_until="domcontentloaded")
                await context.pages[0].wait_for_timeout(300_000)
            finally:
                await context.close()
