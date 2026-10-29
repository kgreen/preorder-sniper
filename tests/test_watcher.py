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


def test_watch_forever_retries_failed_callback(monkeypatch):
    product = Product(
        retailer="amazon",
        name="Test Product",
        url="https://example.com/product",
        available_selector="#available",
        add_to_cart_selector="#add-to-cart",
        checkout_selector="#checkout",
    )
    results = iter(
        [
            StockResult(product=product, available=True, detail="availability marker found"),
            StockResult(product=product, available=True, detail="availability marker found"),
        ]
    )

    class DummyWatcher:
        async def check(self, product):
            return next(results)

    callback_calls = []

    async def callback(result):
        callback_calls.append(result.product.name)
        if len(callback_calls) == 1:
            raise RuntimeError("temporary delivery failure")

    sleep_calls = 0

    async def stop_after_second_sleep(_seconds):
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls >= 2:
            raise RuntimeError("stop loop")

    monkeypatch.setattr("preorder_sniper.watcher.asyncio.sleep", stop_after_second_sleep)

    with pytest.raises(RuntimeError, match="stop loop"):
        asyncio.run(watch_forever(DummyWatcher(), [product], 0, 0, callback))

    assert callback_calls == ["Test Product", "Test Product"]
