# Data Model: retailer stock monitor

## Entities

### Product

Represents a single item being watched.

- `retailer`: human-readable retailer name, for example `amazon`
- `name`: user-facing item name
- `url`: product URL or retailer page link
- `available_selector`: selector used to confirm visible availability 
- `add_to_cart_selector`: selector used to initiate the add-to-cart flow
- `checkout_selector`: selector used to continue to checkout

### StockResult

Represents the latest observed state for one product.

- `product`: the product instance being evaluated
- `available`: boolean status
- `detail`: short explanation for logging or debugging

### Settings

Represents runtime configuration.

- `poll_interval_seconds`: loop delay between checks
- `poll_jitter_seconds`: slight randomness to reduce lockstep requests
- `request_timeout_seconds`: HTTP timeout budget
- `webhook_url`: optional alert destination

### BrowserSession

Represents the local persistent browser state.

- `browser_data_dir`: local profile directory on disk
- `headless`: whether the browser UI is hidden while running
- `logged_in_state`: browser cookies and auth state retained from prior user sessions
