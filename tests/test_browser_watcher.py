import asyncio
from pathlib import Path

import httpx
import pytest
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from preorder_sniper import browser_watcher
from preorder_sniper.browser_watcher import BrowserBusyError, BrowserWatcher
from preorder_sniper.models import Product, StockResult
from preorder_sniper.watcher import BlockedError, rate_limit_delay

AMAZON = Product("amazon", "P", "https://example.com/a", "#a", "#b", "#c")
BESTBUY = Product("bestbuy", "B", "https://example.com/b", ".add-to-cart-button", "#b", "#c")
TARGET = Product("target", "P", "https://example.com/t", "#a", "#b", "#c")

AMAZON_CAPTCHA = '<form action="/errors/validateCaptcha">'
BESTBUY_INTERRUPTION = "<html><body><h1>Pardon Our Interruption</h1></body></html>"
BESTBUY_ACCESS_DENIED = "<html><head><title>Access Denied</title></head></html>"


class FakeHttp:
    def __init__(self):
        self.checked = []

    async def check(self, product):
        self.checked.append(product)
        return StockResult(product, False, "http")

    async def close(self):
        pass


class FakeResponse:
    def __init__(self, status=200, headers=None):
        self.status = status
        self.headers = headers or {}


def _fake_playwright(monkeypatch, pages, marker=True, response=None, goto_error=None, launches=None):
    """pages: HTML returned by successive page.content() calls (last one repeats)."""
    launches = launches if launches is not None else []
    contents = list(pages)

    class Locator:
        @property
        def first(self):
            return self

        async def wait_for(self, **kwargs):
            if not marker:
                raise PlaywrightTimeoutError("timeout")

    class Page:
        async def goto(self, url, **kwargs):
            if goto_error:
                raise goto_error
            return response if response is not None else FakeResponse()

        async def content(self):
            return contents.pop(0) if len(contents) > 1 else contents[0]

        def locator(self, selector):
            return Locator()

    class Context:
        async def new_page(self):
            return Page()

        async def close(self):
            pass

    class Chromium:
        async def launch_persistent_context(self, path, **kwargs):
            launches.append(path)
            return Context()

    class Manager:
        async def __aenter__(self):
            return type("P", (), {"chromium": Chromium()})()

        async def __aexit__(self, *exc):
            pass

    monkeypatch.setattr(browser_watcher, "async_playwright", lambda: Manager())
    return launches


def _watcher(http=None, lock=None):
    return BrowserWatcher(http or FakeHttp(), Path("profile"), headless=True, profile_lock=lock)


def test_browser_check_reports_availability(monkeypatch):
    launches = _fake_playwright(monkeypatch, ["<html></html>"])

    result = asyncio.run(_watcher().check(AMAZON))

    assert result.available and result.detail == "availability marker found"
    assert launches == ["profile"]


def test_browser_check_reports_marker_missing_after_bounded_wait(monkeypatch):
    _fake_playwright(monkeypatch, ["<html></html>"], marker=False)

    assert not asyncio.run(_watcher().check(AMAZON)).available


@pytest.mark.parametrize(
    "product,html",
    [
        (AMAZON, AMAZON_CAPTCHA),
        (BESTBUY, BESTBUY_INTERRUPTION),
        (BESTBUY, BESTBUY_ACCESS_DENIED),
    ],
)
def test_browser_check_stops_on_challenge_without_retrying(monkeypatch, product, html):
    launches = _fake_playwright(monkeypatch, [html])
    watcher = _watcher()

    async def run():
        for _ in range(2):
            with pytest.raises(BlockedError):
                await watcher.check(product)

    asyncio.run(run())

    assert len(launches) == 1


def test_browser_check_rechecks_for_challenge_after_render(monkeypatch):
    _fake_playwright(monkeypatch, ["<html></html>", BESTBUY_INTERRUPTION])

    with pytest.raises(BlockedError):
        asyncio.run(_watcher().check(BESTBUY))


def test_browser_check_surfaces_429_retry_after_to_backoff(monkeypatch):
    _fake_playwright(monkeypatch, ["<html>slow down</html>"], response=FakeResponse(429, {"retry-after": "120"}))

    with pytest.raises(httpx.HTTPStatusError) as excinfo:
        asyncio.run(_watcher().check(AMAZON))

    assert rate_limit_delay(excinfo.value, 5) == 120


def test_browser_check_challenge_takes_precedence_over_error_status(monkeypatch):
    _fake_playwright(monkeypatch, [AMAZON_CAPTCHA], response=FakeResponse(503))

    with pytest.raises(BlockedError):
        asyncio.run(_watcher().check(AMAZON))


def test_browser_check_treats_navigation_failure_as_error(monkeypatch):
    _fake_playwright(monkeypatch, ["<html></html>"], goto_error=PlaywrightTimeoutError("nav timeout"))

    with pytest.raises(PlaywrightTimeoutError):
        asyncio.run(_watcher().check(AMAZON))


def test_busy_profile_defers_browser_checks_without_blocking_http(monkeypatch):
    launches = _fake_playwright(monkeypatch, ["<html></html>"])
    http = FakeHttp()
    lock = asyncio.Lock()
    watcher = _watcher(http, lock)

    async def run():
        async with lock:
            with pytest.raises(BrowserBusyError):
                await asyncio.wait_for(watcher.check(AMAZON), timeout=1)
            await asyncio.wait_for(watcher.check(TARGET), timeout=1)

    asyncio.run(run())

    assert http.checked == [TARGET] and launches == []


def test_other_retailers_use_http(monkeypatch):
    launches = _fake_playwright(monkeypatch, [""])
    http = FakeHttp()

    asyncio.run(_watcher(http).check(TARGET))

    assert http.checked == [TARGET] and launches == []
