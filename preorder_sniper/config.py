from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from .models import Product


def _as_optional_string(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized


def _require_http_url(value: str | None, *, field_name: str) -> str | None:
    normalized = _as_optional_string(value, field_name=field_name)
    if normalized is None:
        return None
    if not re.match(r"^https?://", normalized):
        raise ValueError(f"{field_name} must be an http or https URL.")
    return normalized


def _require_positive_number(value: str | None, *, field_name: str) -> float:
    raw = value if value is not None else "0"
    try:
        number = float(raw)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a number.") from exc
    if number <= 0:
        raise ValueError(f"{field_name} must be greater than zero.")
    return number


def _require_non_negative_number(value: str | None, *, field_name: str) -> float:
    raw = value if value is not None else "0"
    try:
        number = float(raw)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a number.") from exc
    if number < 0:
        raise ValueError(f"{field_name} must be zero or greater.")
    return number


@dataclass(frozen=True)
class Settings:
    poll_interval_seconds: float
    poll_jitter_seconds: float
    request_timeout_seconds: float
    webhook_url: str | None
    sms_to_number: str | None
    sms_from_number: str | None
    twilio_account_sid: str | None
    twilio_auth_token: str | None


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        poll_interval_seconds=_require_positive_number(
            os.getenv("POLL_INTERVAL_SECONDS", "5"), field_name="POLL_INTERVAL_SECONDS"
        ),
        poll_jitter_seconds=_require_non_negative_number(
            os.getenv("POLL_JITTER_SECONDS", "1"), field_name="POLL_JITTER_SECONDS"
        ),
        request_timeout_seconds=_require_positive_number(
            os.getenv("REQUEST_TIMEOUT_SECONDS", "10"), field_name="REQUEST_TIMEOUT_SECONDS"
        ),
        webhook_url=_require_http_url(os.getenv("WEBHOOK_URL"), field_name="WEBHOOK_URL"),
        sms_to_number=_as_optional_string(os.getenv("SMS_TO_NUMBER"), field_name="SMS_TO_NUMBER"),
        sms_from_number=_as_optional_string(
            os.getenv("TWILIO_FROM_NUMBER") or os.getenv("SMS_FROM_NUMBER"),
            field_name="TWILIO_FROM_NUMBER",
        ),
        twilio_account_sid=_as_optional_string(
            os.getenv("TWILIO_ACCOUNT_SID") or os.getenv("SMS_ACCOUNT_SID"),
            field_name="TWILIO_ACCOUNT_SID",
        ),
        twilio_auth_token=_as_optional_string(
            os.getenv("TWILIO_AUTH_TOKEN") or os.getenv("SMS_AUTH_TOKEN"),
            field_name="TWILIO_AUTH_TOKEN",
        ),
    )


def load_products(path: Path) -> list[Product]:
    records = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError("Product configuration must be a JSON array.")

    required = {
        "retailer",
        "name",
        "url",
        "available_selector",
        "add_to_cart_selector",
        "checkout_selector",
    }
    products = []
    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            raise ValueError(f"Product {index} must be an object.")
        if set(record) != required:
            raise ValueError(
                f"Product {index} must contain exactly: {', '.join(sorted(required))}."
            )

        normalized = {
            key: (str(value).strip() if isinstance(value, str) else value)
            for key, value in record.items()
        }
        product = Product(**normalized)

        if not product.retailer:
            raise ValueError(f"Product {index} retailer must not be empty.")
        if not product.name:
            raise ValueError(f"Product {index} name must not be empty.")
        if not product.url:
            raise ValueError(f"Product {index} URL must not be empty.")
        if not re.match(r"^https?://", product.url):
            raise ValueError(f"Product {index} URL must be an http or https URL.")
        for selector_name in (
            "available_selector",
            "add_to_cart_selector",
            "checkout_selector",
        ):
            value = getattr(product, selector_name)
            if not value:
                raise ValueError(f"Product {index} {selector_name} must not be empty.")

        products.append(product)
    return products
