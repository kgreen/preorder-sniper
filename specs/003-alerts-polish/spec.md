# Feature specification: SMS and webhook alert polish

**Issue**: #21 | **Builds on**: 001-retailer-stock-monitor

## User story

As a single user, I want reliable, quiet, safe alerts so a flaky webhook or SMS provider never
stops monitoring, spams me, or leaks secrets.

## Requirements

- FR-001: Each channel request has a timeout and is retried (3 attempts, backoff) on network errors, 429, and 5xx; other 4xx are not retried.
- FR-002: Alert failures never raise; one failing channel does not block the other.
- FR-003: Repeat alerts for the same product are suppressed within `ALERT_COOLDOWN_SECONDS` (default 300; 0 disables).
- FR-004: Partial SMS config or non-E.164 numbers fail at startup with a clear error.
- FR-005: Logs never contain the webhook URL, Twilio credentials, or response bodies.

## Success criteria

- Tests cover retry, non-retryable failure, exhausted retries, dedupe, cooldown expiry, and config validation.
- README documents alert configuration.
