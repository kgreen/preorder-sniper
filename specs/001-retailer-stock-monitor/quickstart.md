# Quickstart: retailer stock monitor

1. Install project dependencies using the repo's Python environment settings.
2. Copy `.env.example` to `.env` and update the values for your preferred polling interval and your SMS/webhook alert settings.
3. Copy `products.example.json` to `products.json` and replace placeholder product URLs and selectors with real, valid retailer pages for Amazon, Target, and Best Buy.
4. Sign in to each retailer once in a persistent browser profile.
5. Run the CLI in alert-only mode to validate detection before turning on checkout automation.
6. Enable checkout support only after a retailer session is confirmed and the user has reviewed the safety constraints and explicitly approved final submission.

## Commands

```powershell
uv run python -m preorder_sniper.cli --products products.json --browser-data-dir .browser-profile
uv run python -m preorder_sniper.cli --products products.json --browser-data-dir .browser-profile --auto-checkout
```
