# preorder-sniper

Single-user stock watcher and assisted checkout for limited preorders at Amazon, Target,
Best Buy, and Walmart.

## Setup

Requires Python 3.11+.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
playwright install chromium
Copy-Item .env.example .env
Copy-Item products.example.json products.json
```

Replace the sample URLs in `products.json` with the exact product pages you want to monitor.
Selectors can change without notice, so use each retailer's live product page and the browser's
Developer Tools to confirm the exact CSS selectors before a release. The app validates product
URLs and polling settings before the watcher starts, and it supports either webhook alerts, SMS
alerts, or both at the same time.

For each retailer item, keep the `url`, `available_selector`, `add_to_cart_selector`, and
`checkout_selector` aligned to the current page markup. The included `products.example.json` uses
representative retailer URL shapes as a starting point, but a valid monitor must be updated to the
specific product page and selector values for the item you are tracking.

Walmart is included in the sample configuration as an explicit retailer target, but its selectors are
still likely to need page-specific validation. In practice, Walmart product pages often use
`data-automation-id` or `data-testid` markup, and they can also challenge automated requests.
Before enabling a Walmart run, confirm the live page still contains the configured selectors with
`--validate-selectors` and keep the project's no-bypass safety policy intact.

**Known limitation:** the watcher polls pages over plain HTTP, and retailers may block or
challenge that traffic. In a 2026-10-29 check, Amazon returned a CAPTCHA page (logged as
`served an anti-bot challenge page` rather than "not available"), Best Buy timed out, and the
sample Target URL returned 404. Walmart should be treated the same way: validate against the live
page and do not attempt to bypass anti-bot protections. If a retailer blocks plain requests, rely
on its own in-stock notifications for that item or use the alert-only flow with a different
availability source. Sample URLs in `products.example.json` may be stale, so always use a current
product URL.

Sign in to each retailer once using the browser profile that the tool will reuse:

```powershell
preorder-sniper --browser-data-dir .browser-profile --login
```

Validate the live selectors before a long monitoring run:

```powershell
preorder-sniper --browser-data-dir .browser-profile --validate-selectors
```

This opens the configured retailer pages in the persistent browser profile, checks each saved selector
against the live page, and reports missing selectors or captured anti-bot challenge pages without
bypassing retailer protections.

Then run the monitor:

```powershell
preorder-sniper --browser-data-dir .browser-profile
```

By default the monitor only sends alerts. Add `--auto-checkout` to opt in to browser automation, or
`--dry-run` to only log availability (no alerts, no browser).

When an availability marker appears, the tool logs and can send both SMS and webhook alerts,
and, only when `--auto-checkout` is set, adds the product to the cart and opens checkout in the
saved browser profile for ten
minutes. It **requires explicit user approval before any final order submission** and does not
bypass CAPTCHAs or queue rules. Review the order and place it manually when you are ready.

Use the retailer sites in accordance with their terms. Keep `products.json`, `.env`, and the
browser profile private; do not store credentials or payment details in this repository.
