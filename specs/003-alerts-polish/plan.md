# Plan: alerts polish

- `notifier.py`: `_deliver` retry wrapper, configurable timeout/cooldown, per-URL dedupe, sanitized logging, Twilio auth via httpx `auth=`.
- `config.py`: `ALERT_COOLDOWN_SECONDS`, `_validate_sms`.
- `cli.py`: pass timeout and cooldown to `Notifier`.
- Tests in `tests/test_notifier.py` and `tests/test_config.py`; README "Alerts" section and `.env.example`.
