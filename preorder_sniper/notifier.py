from __future__ import annotations

import base64
import logging

import httpx

from .models import StockResult

logger = logging.getLogger(__name__)


class Notifier:
    def __init__(
        self,
        webhook_url: str | None = None,
        sms_to_number: str | None = None,
        sms_from_number: str | None = None,
        twilio_account_sid: str | None = None,
        twilio_auth_token: str | None = None,
    ) -> None:
        self._webhook_url = webhook_url
        self._sms_to_number = sms_to_number
        self._sms_from_number = sms_from_number
        self._twilio_account_sid = twilio_account_sid
        self._twilio_auth_token = twilio_auth_token

    async def stock_available(self, result: StockResult) -> None:
        message = (
            f"IN STOCK: {result.product.name} at {result.product.retailer}\n"
            f"{result.product.url}"
        )
        logger.warning(message)

        if self._webhook_url:
            try:
                await self._send_webhook(message)
            except Exception:
                logger.exception("Webhook notification failed for %s.", result.product.name)

        if self._sms_to_number and self._sms_from_number and self._twilio_account_sid and self._twilio_auth_token:
            try:
                await self._send_sms(message)
            except Exception:
                logger.exception("SMS notification failed for %s.", result.product.name)

    async def _send_webhook(self, message: str) -> None:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(self._webhook_url, json={"text": message})
            response.raise_for_status()

    async def _send_sms(self, message: str) -> None:
        account_sid = self._twilio_account_sid
        auth_token = self._twilio_auth_token
        encoded = base64.b64encode(f"{account_sid}:{auth_token}".encode("utf-8")).decode("ascii")
        payload = {
            "To": self._sms_to_number,
            "From": self._sms_from_number,
            "Body": message[:1600],
        }
        auth = f"Basic {encoded}"
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json",
                data=payload,
                headers={"Authorization": auth},
            )
            response.raise_for_status()
