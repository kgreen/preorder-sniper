import asyncio

import httpx
import pytest

from preorder_sniper.models import Product, StockResult
from preorder_sniper.watcher import (
    rate_limit_delay,
    selector_marker,
    selector_matches_html,
    watch_forever,
)


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


def _status_error(code, headers=None):
    request = httpx.Request("GET", "https://example.com")
    response = httpx.Response(code, headers=headers, request=request)
    return httpx.HTTPStatusError("err", request=request, response=response)


def test_rate_limit_delay_honors_retry_after_and_ignores_other_errors():
    assert rate_limit_delay(_status_error(429, {"Retry-After": "30"}), 5) == 30
    assert rate_limit_delay(_status_error(429), 5) == 30
    assert rate_limit_delay(_status_error(500), 5) == 0
    assert rate_limit_delay(RuntimeError("x"), 5) == 0


def test_watch_forever_skips_product_during_429_backoff(monkeypatch):
    product = Product("amazon", "P", "https://example.com", "#a", "#b", "#c")
    checks = 0

    class DummyWatcher:
        async def check(self, product):
            nonlocal checks
            checks += 1
            raise _status_error(429, {"Retry-After": "300"})

    sleeps = 0

    async def fake_sleep(_seconds):
        nonlocal sleeps
        sleeps += 1
        if sleeps >= 3:
            raise RuntimeError("stop loop")

    monkeypatch.setattr("preorder_sniper.watcher.asyncio.sleep", fake_sleep)

    with pytest.raises(RuntimeError, match="stop loop"):
        asyncio.run(watch_forever(DummyWatcher(), [product], 1, 0, None))

    assert checks == 1


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
