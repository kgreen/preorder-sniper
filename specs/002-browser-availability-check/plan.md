# Plan: browser-based availability check

- New `preorder_sniper/browser_watcher.py`: `BrowserWatcher` wraps the HTTP `ProductWatcher`, same
  `check()`/`close()` interface, so `watch_forever` is unchanged.
- `cli.py`: `--browser-check` flag; shares the existing profile lock with checkout.
- Anti-bot detection reuses `is_block_page`; a block adds the product to a stopped set.
- Tests in `tests/test_browser_watcher.py` with a faked Playwright; README updated.
