# Research: retailer stock monitoring

## Problem

The tool needs to detect availability on retailer pages quickly enough to act before stock disappears, while preserving safe user review and respecting the retailer's terms.

## Findings

### Polling vs page rendering

Polling a retailer product URL is simpler than rendering JavaScript-heavy pages, but it can still be brittle because the product page often contains dynamic stock state hidden behind client-side logic or marketplace APIs.

### Selector strategy

A site-specific selector is more reliable than a broad CSS guess. The project should keep the selectors in configuration files, not hard-coded across the codebase, because markup changes are common on major retailer pages.

### Alert path

Fast alerts are valuable only if they reach the user quickly and carry actionable context. Webhook delivery and a direct product URL are a useful baseline, while SMS or push notifications are optional enhancements.

### Browser automation

Browser automation reduces manual friction after detection but has two important limits: it still requires a valid logged-in session and it should not be the only safety gate. The checkout flow should stop before the order is submitted.

## Decision

Use a small Python CLI with a separate watcher, notifier, and Playwright-based browser helper. This keeps the architecture simple, reviewable, and aligned with the project's single-user constraints.
