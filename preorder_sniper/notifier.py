from __future__ import annotations

import asyncio
import logging
import time

import httpx

from .models import StockResult

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_RETRY_DELAY_SECONDS = 1.0
DEFAULT_COOLDOWN_SECONDS = 300.0


def _describe_error(exc: Exception) -> str:
    """Summarize an error without URLs, credentials, or response bodies."""
    if isinstance(exc, httpx.HTTPStatusError):
        return f"HTTP {exc.response.status_code}"
    return type(exc).__name__


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        return status == 429 or status >= 500
    return True


class Notifier:
    def __init__(
        self,
        webhook_url: str | None = None,
        sms_to_number: str | None = None,
        sms_from_number: str | None = None,
        twilio_account_sid: str | None = None,
        twilio_auth_token: str | None = None,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        retry_delay_seconds: float = DEFAULT_RETRY_DELAY_SECONDS,
        cooldown_seconds: float = DEFAULT_COOLDOWN_SECONDS,
    ) -> None:
        self._webhook_url = webhook_url
        self._sms_to_number = sms_to_number
        self._sms_from_number = sms_from_number
        self._twilio_account_sid = twilio_account_sid
        self._twilio_auth_token = twilio_auth_token
        self._timeout = timeout_seconds
        self._max_attempts = max(1, max_attempts)
        self._retry_delay = retry_delay_seconds
        self._cooldown = cooldown_seconds
        self._last_alert: dict[str, float] = {}

    def _should_alert(self, key: str) -> bool:
        now = time.monotonic()
        last = self._last_alert.get(key)
        if last is not None and now - last < self._cooldown:
            return False
        self._last_alert[key] = now
        return True

    async def stock_available(self, result: StockResult) -> None:
        message = (
            f"IN STOCK: {result.product.name} at {result.product.retailer}\n"
            f"{result.product.url}"
        )
        logger.warning(message)

        if not self._should_alert(result.product.url):
            logger.info("Suppressing repeat alert for %s (cooldown active).", result.product.name)
            return

        if self._webhook_url:
            await self._deliver("Webhook", result.product.name, self._send_webhook, message)

        if self._sms_to_number and self._sms_from_number and self._twilio_account_sid and self._twilio_auth_token:
            await self._deliver("SMS", result.product.name, self._send_sms, message)

    async def _deliver(self, channel: str, product_name: str, send, message: str) -> None:
        """Send with retries; never raises so alert failures cannot stop monitoring."""
        for attempt in range(1, self._max_attempts + 1):
            try:
                await send(message)
                return
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                final = attempt == self._max_attempts or not _is_retryable(exc)
                logger.log(
                    logging.ERROR if final else logging.WARNING,
                    "%s notification for %s failed (attempt %d/%d): %s",
                    channel,
                    product_name,
                    attempt,
                    self._max_attempts,
                    _describe_error(exc),
                )
                if final:
                    return
                await asyncio.sleep(self._retry_delay * attempt)

    async def _send_webhook(self, message: str) -> None:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(self._webhook_url, json={"text": message})
            response.raise_for_status()

    async def _send_sms(self, message: str) -> None:
        account_sid = self._twilio_account_sid
        payload = {
            "To": self._sms_to_number,
            "From": self._sms_from_number,
            "Body": message[:1600],
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json",
                data=payload,
                auth=(account_sid, self._twilio_auth_token),
            )
            response.raise_for_status()
