import json

import pytest

from preorder_sniper.config import load_products, load_settings


def test_load_products_rejects_incomplete_product(tmp_path):
    products_file = tmp_path / "products.json"
    products_file.write_text(json.dumps([{"retailer": "amazon"}]), encoding="utf-8")

    with pytest.raises(ValueError, match="exactly"):
        load_products(products_file)


def test_load_settings_reads_sms_and_webhook_channels(monkeypatch):
    monkeypatch.setenv("WEBHOOK_URL", "https://example.com/webhook")
    monkeypatch.setenv("SMS_TO_NUMBER", "+15555550123")
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "sid")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "token")
    monkeypatch.setenv("TWILIO_FROM_NUMBER", "+15555550124")

    settings = load_settings()

    assert settings.webhook_url == "https://example.com/webhook"
    assert settings.sms_to_number == "+15555550123"
    assert settings.sms_from_number == "+15555550124"
    assert settings.twilio_account_sid == "sid"
    assert settings.twilio_auth_token == "token"


def test_load_products_rejects_non_http_urls(tmp_path):
    products_file = tmp_path / "products.json"
    products_file.write_text(
        json.dumps(
            [
                {
                    "retailer": "amazon",
                    "name": "Widget",
                    "url": "ftp://example.com/product",
                    "available_selector": "#available",
                    "add_to_cart_selector": "#add-to-cart",
                    "checkout_selector": "#checkout",
                }
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="http or https URL"):
        load_products(products_file)


def test_load_settings_rejects_invalid_numeric_values(monkeypatch):
    monkeypatch.setenv("POLL_INTERVAL_SECONDS", "0")

    with pytest.raises(ValueError, match="greater than zero"):
        load_settings()
