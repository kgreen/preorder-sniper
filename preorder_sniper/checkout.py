from __future__ import annotations

import logging
from pathlib import Path

from playwright.async_api import async_playwright

from .models import Product
from .watcher import is_block_page

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

    async def validate_products(self, products: list[Product]) -> None:
        """Open each configured retailer page and confirm the saved selectors still exist."""
        async with async_playwright() as playwright:
            context = await playwright.chromium.launch_persistent_context(
                str(self._browser_data_dir),
                headless=self._headless,
            )
            try:
                for product in products:
                    page = await context.new_page()
                    logger.info("Validating selectors for %s (%s)", product.name, product.retailer)
                    try:
                        await page.goto(product.url, wait_until="domcontentloaded", timeout=30_000)
                    except Exception:
                        logger.warning(
                            "Selector validation could not load %s at %s; skipping browser validation.",
                            product.name,
                            product.url,
                        )
                        continue

                    if is_block_page(await page.content()):
                        logger.warning(
                            "%s (%s) served an anti-bot challenge page; selector validation was skipped without bypassing protections.",
                            product.name,
                            product.retailer,
                        )
                        continue

                    selector_results = []
                    for label, selector in (
                        ("available", product.available_selector),
                        ("add to cart", product.add_to_cart_selector),
                        ("checkout", product.checkout_selector),
                    ):
                        try:
                            found = await page.locator(selector).count() > 0
                        except Exception:
                            found = False
                        selector_results.append(found)
                        status = "FOUND" if found else "MISSING"
                        logger.info(
                            "%s %s selector for %s: %s (%s)",
                            product.name,
                            label,
                            product.retailer,
                            status,
                            selector,
                        )

                    if all(selector_results):
                        logger.info("Selector validation succeeded for %s (%s).", product.name, product.retailer)
                    else:
                        logger.warning(
                            "Selector validation found missing selectors for %s (%s).",
                            product.name,
                            product.retailer,
                        )
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
