# Implementation Plan: retailer stock monitor

**Branch**: `001-retailer-stock-monitor` | **Date**: 2026-10-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-retailer-stock-monitor/spec.md`

## Summary

This feature delivers a single-user stock watcher for retailer preorder pages. It polls configured product URLs, detects availability signals, alerts the user quickly, and optionally reuses a persistent browser profile to accelerate the add-to-cart and checkout flow without automatically placing an order.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: httpx, playwright, python-dotenv, pytest

**Storage**: Local configuration files, environment variables, and persistent browser profile data

**Testing**: pytest and small functional smoke checks

**Target Platform**: Local workstation or laptop running Windows/macOS/Linux

**Project Type**: CLI application

**Performance Goals**: Poll configured products on a near-real-time loop with short intervals and jitter while preserving retailer etiquette and avoiding duplicate alerts

**Constraints**: One user, no secret storage in Git, no automatic purchase submission, no CAPTCHA bypass, explicit selector maintenance

**Scale/Scope**: Several retailers and a small number of tracked products at a time

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Privacy-first automation: PASS - secrets are isolated in `.env` and browser profile.
- Safe-by-default checkout: PASS - manual final review remains required before purchase.
- Testable monitoring and alerting: PASS - Python CLI and unit tests are in place.
- Single-user low-noise operation: PASS - polling uses jitter and bounded retry behavior.
- Explicit retailer compatibility: PASS - each site relies on explicit selectors and product configuration.

## Project Structure

```text
preorder_sniper/
├── __init__.py
├── cli.py
├── config.py
├── models.py
├── notifier.py
├── watcher.py
├── checkout.py
├──

tests/
├── test_config.py
├── test_watcher.py
```

**Structure Decision**: Keep the project as a small Python CLI with one folder for retailer-monitor logic and a separate tests directory. This matches the current repository structure and allows product configuration to stay local and explicit.

## Research Findings

- Fast polling is valuable because availability can disappear in seconds, but the visible site may not expose a clean machine-readable signal.
- Browser automation is most useful after stock is already detected; it reduces the manual steps required to reach checkout.
- Alert delivery should be separate from checkout logic so the user can choose alert-only or alert-plus-browser mode.
- Explicit selectors and local configuration are the key risks to manage because retailer HTML changes often.

## Data Model

- `Product`: retailer, name, URL, selectors, and metadata required to detect availability.
- `StockResult`: the product, boolean availability, and a human-readable explanation.
- `Settings`: polling interval, timeout values, and optional alert endpoint.
- `BrowserSession`: local persistent profile data that keeps the retailer sign-in state available to Playwright.

## Quickstart

1. Copy `.env.example` to `.env` and set the desired polling interval and optional webhook URL.
2. Copy `products.example.json` to `products.json` and populate the actual retailer product URLs and selectors.
3. Sign in through the persistent browser profile once, then run the CLI in alert-only mode to validate detection.
4. When the site is stable, enable the browser automation path and review the checkout flow before final purchase.
5. Run the automated tests before releasing a new configuration or selector update.

## Complexity Tracking

No constitution violations require complexity exceptions for this feature.
