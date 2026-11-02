import asyncio

import httpx

from preorder_sniper.models import Product, StockResult
from preorder_sniper.notifier import Notifier


class DummyResponse:
    def __init__(self, status_code=200):
        self.status_code = status_code

    def raise_for_status(self):
        return None


class DummyClient:
    def __init__(self, *args, **kwargs):
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def post(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        return DummyResponse()


def test_notifier_sends_webhook_and_sms(monkeypatch):
    product = Product(
        retailer="amazon",
        name="Metroid Ravenous: Special Edition",
        url="https://example.com/product",
        available_selector="#add-to-cart-button",
        add_to_cart_selector="#add-to-cart-button",
        checkout_selector="#checkout",
    )
    result = StockResult(product=product, available=True, detail="availability marker found")

    clients = []

    def fake_async_client(*args, **kwargs):
        client = DummyClient(*args, **kwargs)
        clients.append(client)
        return client

    monkeypatch.setattr("preorder_sniper.notifier.httpx.AsyncClient", fake_async_client)

    notifier = Notifier(
        webhook_url="https://example.com/hook",
        sms_to_number="+15555550123",
        sms_from_number="+15555550124",
        twilio_account_sid="sid",
        twilio_auth_token="token",
    )

    asyncio.run(notifier.stock_available(result))

    assert len(clients) == 2
    assert clients[0].calls[0]["url"] == "https://example.com/hook"
    assert clients[1].calls[0]["url"].startswith("https://api.twilio.com/")
    assert clients[1].calls[0]["data"]["To"] == "+15555550123"
    assert clients[1].calls[0]["data"]["From"] == "+15555550124"


def test_notifier_continues_after_channel_failure(monkeypatch):
    product = Product(
        retailer="amazon",
        name="Metroid Ravenous: Special Edition",
        url="https://example.com/product",
        available_selector="#add-to-cart-button",
        add_to_cart_selector="#add-to-cart-button",
        checkout_selector="#checkout",
    )
    result = StockResult(product=product, available=True, detail="availability marker found")

    class FailingWebhookClient(DummyClient):
        async def post(self, url, **kwargs):
            if url == "https://example.com/hook":
                raise httpx.HTTPError("webhook outage")
            return await super().post(url, **kwargs)

    clients = []

    def fake_async_client(*args, **kwargs):
        client = FailingWebhookClient(*args, **kwargs)
        clients.append(client)
        return client

    monkeypatch.setattr("preorder_sniper.notifier.httpx.AsyncClient", fake_async_client)
    notifier = Notifier(
        webhook_url="https://example.com/hook",
        sms_to_number="+15555550123",
        sms_from_number="+15555550124",
        twilio_account_sid="sid",
        twilio_auth_token="token",
        retry_delay_seconds=0,
    )

    asyncio.run(notifier.stock_available(result))

    assert len(clients) == 4  # 3 webhook attempts, then SMS
    assert all(c.calls == [] for c in clients[:3])
    assert clients[3].calls[0]["data"]["To"] == "+15555550123"


def _result():
    product = Product(
        retailer="amazon",
        name="Widget",
        url="https://example.com/product",
        available_selector="a",
        add_to_cart_selector="b",
        checkout_selector="c",
    )
    return StockResult(product=product, available=True, detail="x")


def _notifier(**kwargs):
    return Notifier(
        webhook_url="https://example.com/hook?token=SECRET",
        retry_delay_seconds=0,
        **kwargs,
    )


def _status_error(code):
    request = httpx.Request("POST", "https://example.com/hook?token=SECRET")
    return httpx.HTTPStatusError("boom", request=request, response=httpx.Response(code, request=request))


def _patch_client(monkeypatch, outcomes):
    calls = []

    class Client(DummyClient):
        async def post(self, url, **kwargs):
            calls.append(url)
            outcome = outcomes[min(len(calls), len(outcomes)) - 1]
            if isinstance(outcome, Exception):
                raise outcome
            return DummyResponse()

    monkeypatch.setattr("preorder_sniper.notifier.httpx.AsyncClient", lambda *a, **k: Client())
    return calls


def test_retries_transient_failure_then_succeeds(monkeypatch):
    calls = _patch_client(monkeypatch, [httpx.ConnectTimeout("t"), _status_error(503), None])
    asyncio.run(_notifier().stock_available(_result()))
    assert len(calls) == 3


def test_does_not_retry_client_errors(monkeypatch):
    calls = _patch_client(monkeypatch, [_status_error(400)])
    asyncio.run(_notifier().stock_available(_result()))
    assert len(calls) == 1


def test_gives_up_after_max_attempts_without_raising(monkeypatch):
    calls = _patch_client(monkeypatch, [httpx.ConnectError("down")])
    asyncio.run(_notifier(max_attempts=2).stock_available(_result()))
    assert len(calls) == 2


def test_repeat_alerts_are_deduplicated(monkeypatch):
    calls = _patch_client(monkeypatch, [None])
    notifier = _notifier(cooldown_seconds=60)
    asyncio.run(notifier.stock_available(_result()))
    asyncio.run(notifier.stock_available(_result()))
    assert len(calls) == 1


def test_alert_resumes_after_cooldown(monkeypatch):
    calls = _patch_client(monkeypatch, [None])
    notifier = _notifier(cooldown_seconds=0)
    asyncio.run(notifier.stock_available(_result()))
    asyncio.run(notifier.stock_available(_result()))
    assert len(calls) == 2


def test_logs_do_not_leak_secrets(monkeypatch, caplog):
    _patch_client(monkeypatch, [_status_error(500)])
    notifier = Notifier(
        webhook_url="https://example.com/hook?token=SECRET",
        sms_to_number="+15555550123",
        sms_from_number="+15555550124",
        twilio_account_sid="ACSECRETSID",
        twilio_auth_token="SECRETTOKEN",
        retry_delay_seconds=0,
    )
    with caplog.at_level("DEBUG"):
        asyncio.run(notifier.stock_available(_result()))
    assert "failed" in caplog.text
    for secret in ("SECRET", "ACSECRETSID", "SECRETTOKEN"):
        assert secret not in caplog.text
