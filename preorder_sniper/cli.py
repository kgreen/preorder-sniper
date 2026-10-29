from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from .checkout import AssistedCheckout
from .config import load_products, load_settings
from .notifier import Notifier
from .watcher import ProductWatcher, watch_forever


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Monitor products and launch an assisted checkout when stock appears."
    )
    parser.add_argument("--products", type=Path, default=Path("products.json"))
    parser.add_argument("--browser-data-dir", type=Path, default=Path(".browser-profile"))
    parser.add_argument("--headless", action="store_true")
    parser.add_argument(
        "--login",
        action="store_true",
        help="Open the retailer pages for five minutes so you can sign in to the saved profile.",
    )
    parser.add_argument(
        "--auto-checkout",
        action="store_true",
        help="Opt in: add to cart and open checkout when stock appears (never submits an order).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Monitor and log availability only; send no alerts and open no browser.",
    )
    parser.add_argument(
        "--validate-selectors",
        action="store_true",
        help="Open each configured retailer page in the persistent browser and confirm the configured selectors still match the live page without bypassing anti-bot protections.",
    )
    return parser.parse_args()


def prompt_for_checkout_approval() -> bool:
    if not sys.stdin.isatty():
        logging.getLogger(__name__).warning(
            "Auto-checkout approval skipped because stdin is not interactive; checkout was not started."
        )
        return False
    response = input(
        "Approve opening the saved retailer browser session to add to cart and open checkout? [y/N]: "
    ).strip().lower()
    return response in {"y", "yes"}


async def run(args: argparse.Namespace) -> None:
    settings = load_settings()
    products = load_products(args.products)

    if args.dry_run:
        args.auto_checkout = False
    if args.dry_run and args.login:
        logging.getLogger(__name__).warning("DRY RUN: skipping login workflow so no browser pages are opened.")
        return

    checkout = AssistedCheckout(args.browser_data_dir, args.headless)
    if args.validate_selectors:
        if args.dry_run:
            logging.getLogger(__name__).warning(
                "DRY RUN: selector validation requires a browser session; skipping without opening pages."
            )
            return
        await checkout.validate_products(products)
        return

    notifier = Notifier(
        settings.webhook_url,
        settings.sms_to_number,
        settings.sms_from_number,
        settings.twilio_account_sid,
        settings.twilio_auth_token,
    )
    if args.login:
        await checkout.open_login_pages(products)
        return
    if args.auto_checkout and not prompt_for_checkout_approval():
        logging.getLogger(__name__).warning(
            "Auto-checkout declined; browser automation is disabled for this run."
        )
        args.auto_checkout = False
    watcher = ProductWatcher(settings.request_timeout_seconds)

    checkout_tasks: dict = {}
    # All checkouts share one persistent browser profile, which Chromium locks per process.
    profile_lock = asyncio.Lock()

    async def run_checkout(product) -> None:
        try:
            async with profile_lock:
                await checkout.run(product)
        except Exception:
            logging.getLogger(__name__).exception("Assisted checkout failed for %s", product.name)
        finally:
            checkout_tasks.pop(product, None)

    async def on_available(result) -> None:
        if args.dry_run:
            logging.getLogger(__name__).warning(
                "DRY RUN: %s is available at %s; no alert sent, no checkout opened.",
                result.product.name,
                result.product.url,
            )
            return
        await notifier.stock_available(result)
        if args.auto_checkout and result.product not in checkout_tasks:
            # Run in the background so the 10-minute review window doesn't pause polling.
            checkout_tasks[result.product] = asyncio.create_task(run_checkout(result.product))

    try:
        await watch_forever(
            watcher,
            products,
            settings.poll_interval_seconds,
            settings.poll_jitter_seconds,
            on_available,
        )
    finally:
        await watcher.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(run(parse_args()))


if __name__ == "__main__":
    main()
