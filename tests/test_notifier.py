import asyncio

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
