import argparse
import asyncio
import logging

from preorder_sniper import cli
from preorder_sniper.models import Product, StockResult

PRODUCT = Product("amazon", "P", "https://example.com", "#a", "#b", "#c")


def _args(**overrides):
    values = dict(
        products="p.json", browser_data_dir="profile", headless=True, login=False,
        auto_checkout=False, dry_run=False,
    )
    values.update(overrides)
    return argparse.Namespace(**values)


def _run_with_available_product(monkeypatch, args):
    calls = {"alerts": 0, "checkouts": 0}

    class FakeNotifier:
        def __init__(self, *a):
            pass

        async def stock_available(self, result):
            calls["alerts"] += 1

    class FakeCheckout:
        def __init__(self, *a):
            pass

        async def run(self, product):
            calls["checkouts"] += 1

    class FakeWatcher:
        def __init__(self, *a):
            pass

        async def close(self):
            pass

    async def fake_watch(watcher, products, interval, jitter, on_available):
        await on_available(StockResult(PRODUCT, True, "found"))
        await asyncio.sleep(0)

    monkeypatch.setattr(cli, "load_products", lambda path: [PRODUCT])
    monkeypatch.setattr(cli, "Notifier", FakeNotifier)
    monkeypatch.setattr(cli, "AssistedCheckout", FakeCheckout)
    monkeypatch.setattr(cli, "ProductWatcher", FakeWatcher)
    monkeypatch.setattr(cli, "watch_forever", fake_watch)
    asyncio.run(cli.run(args))
    return calls


def test_dry_run_sends_no_alert_and_opens_no_checkout(monkeypatch, caplog):
    with caplog.at_level(logging.WARNING):
        calls = _run_with_available_product(monkeypatch, _args(dry_run=True))

    assert calls == {"alerts": 0, "checkouts": 0}
    assert "DRY RUN" in caplog.text


def test_auto_checkout_alerts_and_starts_checkout(monkeypatch):
    calls = _run_with_available_product(monkeypatch, _args(auto_checkout=True))

    assert calls == {"alerts": 1, "checkouts": 1}


def test_default_run_alerts_without_browser(monkeypatch):
    calls = _run_with_available_product(monkeypatch, _args())

    assert calls == {"alerts": 1, "checkouts": 0}
