# Feature specification: browser-based availability check

**Issue**: #14 | **Builds on**: 001-retailer-stock-monitor

## User story

As a single user monitoring Amazon and Best Buy, I want an opt-in browser-based availability check
using my persistent Playwright profile, because plain HTTP polling is CAPTCHA-blocked or times out.

## Requirements

- FR-001: `--browser-check` opts in; default behavior (HTTP polling) is unchanged.
- FR-002: Only Amazon and Best Buy use the browser; other retailers keep HTTP polling.
- FR-003: The check reuses the persistent browser profile and never overlaps other browser use.
- FR-004: If an anti-bot/CAPTCHA page is detected, report it and stop checking that product; never bypass.
- FR-005: `--dry-run` never opens a browser, so it ignores `--browser-check`.
- FR-006: No order is ever submitted; alerting and assisted checkout flows are unchanged.

## Success criteria

- Availability is reported from the live page's `available_selector` via Playwright.
- Tests cover found, missing, CAPTCHA stop, and HTTP fallback for other retailers.
