from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from .models import Product


@dataclass(frozen=True)
class Settings:
    poll_interval_seconds: float
    poll_jitter_seconds: float
    request_timeout_seconds: float
    webhook_url: str | None


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        poll_interval_seconds=float(os.getenv("POLL_INTERVAL_SECONDS", "5")),
        poll_jitter_seconds=float(os.getenv("POLL_JITTER_SECONDS", "1")),
        request_timeout_seconds=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "10")),
        webhook_url=os.getenv("WEBHOOK_URL") or None,
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
        if not isinstance(record, dict) or set(record) != required:
            raise ValueError(
                f"Product {index} must contain exactly: {', '.join(sorted(required))}."
            )
        products.append(Product(**record))
    return products
