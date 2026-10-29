import argparse
import asyncio
import logging

from preorder_sniper import cli
from preorder_sniper.models import Product, StockResult

PRODUCT = Product("amazon", "P", "https://example.com", "#a", "#b", "#c")


def _args(**overrides):
    values = dict(
        products="p.json",
        browser_data_dir="profile",
        headless=True,
        login=False,
        auto_checkout=False,
        dry_run=False,
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


def test_dry_run_skips_login_flow(monkeypatch, caplog):
    seen = {"opened": False}

    class FakeCheckout:
        async def open_login_pages(self, products):
            seen["opened"] = True

    monkeypatch.setattr(cli, "load_settings", lambda: type("Settings", (), {
        "webhook_url": None,
        "sms_to_number": None,
        "sms_from_number": None,
        "twilio_account_sid": None,
        "twilio_auth_token": None,
    })())
    monkeypatch.setattr(cli, "load_products", lambda path: [PRODUCT])
    monkeypatch.setattr(cli, "AssistedCheckout", lambda *a, **k: FakeCheckout())
    monkeypatch.setattr(cli, "Notifier", lambda *a, **k: None)
    monkeypatch.setattr(cli, "ProductWatcher", lambda *a, **k: (_ for _ in ()).throw(AssertionError("watcher should not run")))
    monkeypatch.setattr(cli, "watch_forever", lambda *a, **k: (_ for _ in ()).throw(AssertionError("watcher should not run")))

    with caplog.at_level(logging.WARNING):
        asyncio.run(cli.run(_args(login=True, dry_run=True)))

    assert seen["opened"] is False
    assert "DRY RUN" in caplog.text


def test_login_opens_pages_without_watcher(monkeypatch):
    seen = {}

    class FakeCheckout:
        def __init__(self, *a, **k):
            pass

        async def open_login_pages(self, products):
            seen["products"] = products

    monkeypatch.setattr(cli, "load_settings", lambda: type("Settings", (), {
        "webhook_url": None,
        "sms_to_number": None,
        "sms_from_number": None,
        "twilio_account_sid": None,
        "twilio_auth_token": None,
    })())
    monkeypatch.setattr(cli, "load_products", lambda path: [PRODUCT])
    monkeypatch.setattr(cli, "Notifier", lambda *a, **k: None)
    monkeypatch.setattr(cli, "AssistedCheckout", FakeCheckout)
    monkeypatch.setattr(cli, "ProductWatcher", lambda *a, **k: (_ for _ in ()).throw(AssertionError("watcher should not run")))
    monkeypatch.setattr(cli, "watch_forever", lambda *a, **k: (_ for _ in ()).throw(AssertionError("watcher should not run")))

    asyncio.run(cli.run(_args(login=True)))

    assert seen["products"] == [PRODUCT]


def test_auto_checkout_alerts_and_starts_checkout(monkeypatch):
    monkeypatch.setattr(cli, "prompt_for_checkout_approval", lambda: True)
    calls = _run_with_available_product(monkeypatch, _args(auto_checkout=True))

    assert calls == {"alerts": 1, "checkouts": 1}


def test_auto_checkout_logs_background_failures(monkeypatch, caplog):
    class FakeNotifier:
        def __init__(self, *a):
            pass

        async def stock_available(self, result):
            pass

    class FakeCheckout:
        def __init__(self, *a):
            pass

        async def run(self, product):
            raise RuntimeError("checkout crashed")

    class FakeWatcher:
        def __init__(self, *a):
            pass

        async def close(self):
            pass

    async def fake_watch(watcher, products, interval, jitter, on_available):
        await on_available(StockResult(PRODUCT, True, "found"))
        for _ in range(5):
            await asyncio.sleep(0.01)

    monkeypatch.setattr(cli, "prompt_for_checkout_approval", lambda: True)
    monkeypatch.setattr(cli, "load_products", lambda path: [PRODUCT])
    monkeypatch.setattr(cli, "load_settings", lambda: type("Settings", (), {
        "webhook_url": None,
        "sms_to_number": None,
        "sms_from_number": None,
        "twilio_account_sid": None,
        "twilio_auth_token": None,
        "poll_interval_seconds": 0,
        "poll_jitter_seconds": 0,
        "request_timeout_seconds": 1,
    })())
    monkeypatch.setattr(cli, "Notifier", FakeNotifier)
    monkeypatch.setattr(cli, "AssistedCheckout", FakeCheckout)
    monkeypatch.setattr(cli, "ProductWatcher", FakeWatcher)
    monkeypatch.setattr(cli, "watch_forever", fake_watch)

    with caplog.at_level(logging.ERROR):
        asyncio.run(cli.run(_args(auto_checkout=True)))

    assert "Assisted checkout failed for P" in caplog.text


def test_default_run_alerts_without_browser(monkeypatch):
    calls = _run_with_available_product(monkeypatch, _args())

    assert calls == {"alerts": 1, "checkouts": 0}
