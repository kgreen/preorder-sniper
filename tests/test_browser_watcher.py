import asyncio
from pathlib import Path

import pytest

from preorder_sniper import browser_watcher
from preorder_sniper.browser_watcher import BrowserWatcher
from preorder_sniper.models import Product, StockResult
from preorder_sniper.watcher import BlockedError

AMAZON = Product("amazon", "P", "https://example.com/a", "#a", "#b", "#c")
TARGET = Product("target", "P", "https://example.com/t", "#a", "#b", "#c")


class FakeHttp:
    def __init__(self):
        self.checked = []

    async def check(self, product):
        self.checked.append(product)
        return StockResult(product, False, "http")

    async def close(self):
        pass


def _fake_playwright(monkeypatch, html, marker_count, launches):
    class Locator:
        async def count(self):
            return marker_count

    class Page:
        async def goto(self, url, **kwargs):
            pass

        async def content(self):
            return html

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


def _watcher(http):
    return BrowserWatcher(http, Path("profile"), headless=True)


def test_browser_check_reports_availability(monkeypatch):
    launches = []
    _fake_playwright(monkeypatch, "<html></html>", 1, launches)

    result = asyncio.run(_watcher(FakeHttp()).check(AMAZON))

    assert result.available and result.detail == "availability marker found"
    assert launches == ["profile"]


def test_browser_check_reports_marker_missing(monkeypatch):
    _fake_playwright(monkeypatch, "<html></html>", 0, [])

    assert not asyncio.run(_watcher(FakeHttp()).check(AMAZON)).available


def test_browser_check_stops_on_captcha_without_retrying(monkeypatch):
    launches = []
    _fake_playwright(monkeypatch, '<form action="/errors/validateCaptcha">', 1, launches)
    watcher = _watcher(FakeHttp())

    async def run():
        for _ in range(2):
            with pytest.raises(BlockedError):
                await watcher.check(AMAZON)

    asyncio.run(run())

    assert len(launches) == 1


def test_other_retailers_use_http(monkeypatch):
    launches = []
    _fake_playwright(monkeypatch, "", 1, launches)
    http = FakeHttp()

    asyncio.run(_watcher(http).check(TARGET))

    assert http.checked == [TARGET] and launches == []
