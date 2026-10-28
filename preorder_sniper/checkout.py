from __future__ import annotations

from pathlib import Path

from playwright.async_api import async_playwright

from .models import Product


class AssistedCheckout:
    def __init__(self, browser_data_dir: Path, headless: bool = False) -> None:
        self._browser_data_dir = browser_data_dir
        self._headless = headless

    async def run(self, product: Product) -> None:
        """Add the product to cart and open checkout; never submit an order."""
        async with async_playwright() as playwright:
            context = await playwright.chromium.launch_persistent_context(
                str(self._browser_data_dir),
                headless=self._headless,
            )
            page = await context.new_page()
            try:
                await page.goto(product.url, wait_until="domcontentloaded")
                await page.locator(product.add_to_cart_selector).click(timeout=10_000)
                await page.locator(product.checkout_selector).click(timeout=10_000)
                await page.bring_to_front()
                await page.wait_for_timeout(600_000)
            finally:
                await context.close()

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
