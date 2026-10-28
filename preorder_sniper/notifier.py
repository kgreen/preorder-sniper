from __future__ import annotations

import logging

import httpx

from .models import StockResult

logger = logging.getLogger(__name__)


class Notifier:
    def __init__(self, webhook_url: str | None) -> None:
        self._webhook_url = webhook_url

    async def stock_available(self, result: StockResult) -> None:
        message = (
            f"IN STOCK: {result.product.name} at {result.product.retailer}\n"
            f"{result.product.url}"
        )
        logger.warning(message)
        if not self._webhook_url:
            return

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(self._webhook_url, json={"text": message})
            response.raise_for_status()
