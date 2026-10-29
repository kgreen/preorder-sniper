from __future__ import annotations

import asyncio

from preorder_sniper.checkout import AssistedCheckout
from preorder_sniper.models import Product


class DummyLocator:
    def __init__(self, page, selector: str, count: int):
        self.page = page
        self.selector = selector
        self.count_value = count
        self.click_called = False
        self.first = self

    async def click(self, timeout: int | None = None):
        self.click_called = True
        self.page.actions.append(self.selector)

    async def count(self):
        return self.count_value


class DummyPage:
    def __init__(self):
        self.actions = []
        self.locators = {}

    def locator(self, selector: str):
        if selector not in self.locators:
            self.locators[selector] = DummyLocator(self, selector, 1)
        return self.locators[selector]

    async def goto(self, *args, **kwargs):
        self.actions.append("goto")

    async def bring_to_front(self):
        self.actions.append("bring_to_front")

    async def wait_for_timeout(self, _milliseconds):
        self.actions.append("wait_for_timeout")


class DummyContext:
    def __init__(self, page):
        self.page = page
        self.closed = False

    async def close(self):
        self.closed = True

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def new_page(self):
        return self.page


class DummyPlaywright:
    def __init__(self, context):
        self.chromium = self
        self._context = context

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def launch_persistent_context(self, *_args, **kwargs):
        return self._context


def test_assisted_checkout_pauses_before_submit(monkeypatch):
    product = Product(
        retailer="amazon",
        name="Test Product",
        url="https://example.com/product",
        available_selector="#available",
        add_to_cart_selector="#add-to-cart",
        checkout_selector="#checkout",
    )
    page = DummyPage()
    checkout = AssistedCheckout(browser_data_dir="/tmp/profile")

    monkeypatch.setattr("preorder_sniper.checkout.async_playwright", lambda: DummyPlaywright(DummyContext(page)))

    asyncio.run(checkout.run(product))

    assert page.actions == [
        "goto",
        "#add-to-cart",
        "#checkout",
        "bring_to_front",
        "wait_for_timeout",
    ]
    assert page.locators["#add-to-cart"].click_called is True
    assert page.locators["#checkout"].click_called is True


def test_assisted_checkout_raises_when_click_target_is_missing(monkeypatch):
    product = Product(
        retailer="amazon",
        name="Test Product",
        url="https://example.com/product",
        available_selector="#available",
        add_to_cart_selector="#missing-add-to-cart",
        checkout_selector="#checkout",
    )
    page = DummyPage()

    class FailingLocator(DummyLocator):
        async def click(self, timeout: int | None = None):
            raise TimeoutError("selector timed out")

    page.locators["#missing-add-to-cart"] = FailingLocator(page, "#missing-add-to-cart", 1)
    checkout = AssistedCheckout(browser_data_dir="/tmp/profile")

    monkeypatch.setattr("preorder_sniper.checkout.async_playwright", lambda: DummyPlaywright(DummyContext(page)))

    try:
        asyncio.run(checkout.run(product))
        assert False, "TimeoutError was expected"
    except TimeoutError:
        pass
