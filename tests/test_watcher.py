import asyncio

import pytest

from preorder_sniper.models import Product, StockResult
from preorder_sniper.watcher import selector_marker, selector_matches_html, watch_forever


def test_selector_marker_handles_id_and_class_selectors():
    assert selector_marker("#add-to-cart-button") == 'id="add-to-cart-button"'
    assert selector_marker(".add-to-cart-button") == "add-to-cart-button"


def test_selector_matches_html_supports_configured_selector_types():
    html = (
        '<button id="add-to-cart-button"></button>'
        '<button class="button add-to-cart-button"></button>'
        '<button data-test="shipItButton"></button>'
    )

    assert selector_matches_html("#add-to-cart-button", html)
    assert selector_matches_html(".add-to-cart-button", html)
    assert selector_matches_html("[data-test='shipItButton']", html)


def test_watch_forever_only_alerts_on_new_in_stock_period(monkeypatch):
    product = Product(
        retailer="amazon",
        name="Test Product",
        url="https://example.com/product",
        available_selector="#add-to-cart-button",
        add_to_cart_selector="#add-to-cart-button",
        checkout_selector="#checkout",
    )
    results = iter(
        [
            StockResult(product=product, available=True, detail="availability marker found"),
            StockResult(product=product, available=False, detail="availability marker not found"),
            StockResult(product=product, available=True, detail="availability marker found"),
        ]
    )

    class FakeWatcher:
        async def check(self, product_check):
            return next(results)

    sleep_calls = {"count": 0}

    async def fake_sleep(*args, **kwargs):
        sleep_calls["count"] += 1
        if sleep_calls["count"] >= 3:
            raise asyncio.CancelledError

    monkeypatch.setattr("preorder_sniper.watcher.asyncio.sleep", fake_sleep)

    alerts = []

    async def on_available(result):
        alerts.append(result.product.name)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(watch_forever(FakeWatcher(), [product], 0, 0, on_available))

    assert alerts == ["Test Product", "Test Product"]


def test_watch_forever_continues_after_callback_error(monkeypatch):
    product = Product(
        retailer="target",
        name="Target Product",
        url="https://example.com/target",
        available_selector="[data-test='shipItButton']",
        add_to_cart_selector="[data-test='shipItButton']",
        checkout_selector="[data-test='checkout-button']",
    )

    class FakeWatcher:
        async def check(self, product_check):
            return StockResult(product=product, available=True, detail="availability marker found")

    async def fake_sleep(*args, **kwargs):
        raise asyncio.CancelledError

    async def failing_callback(result):
        raise RuntimeError("alert failed")

    monkeypatch.setattr("preorder_sniper.watcher.asyncio.sleep", fake_sleep)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(watch_forever(FakeWatcher(), [product], 0, 0, failing_callback))
