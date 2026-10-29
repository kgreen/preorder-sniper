<!--
Sync Impact Report:
- Version change: template -> 1.0.0
- Modified principles: template placeholders replaced with project-specific governance
- Added sections: "Operational Constraints" and "Development Workflow"
- Removed sections: none
- Deferred items: none
-->

# preorder-sniper Constitution

## Core Principles

### I. Privacy-First Automation
The project MUST keep credentials, payment methods, session cookies, and retailer account state out of the repository and out of logs. Configuration values that are not safe to share MUST live in environment variables, local browser profiles, or explicit secret stores rather than committed files.

This principle protects the user from credential leakage and reduces the chance of accidental exposure during bug reports or public code review.

### II. Safe-by-Default Checkout
The tool MUST prioritize user safety over speed. Any assisted checkout flow MUST stop before submitting an order unless the user explicitly enables a constrained final-submit action after review. It MUST avoid CAPTCHA bypasses, queue skipping, or automated purchase flows that violate retailer terms.

This principle prevents disruptive or policy-breaking behavior and keeps the project aligned with human oversight.

### III. Testable Monitoring and Alerting
Every new monitoring, parsing, or alerting behavior MUST be validated by automated tests or a reproducible smoke path. Default behavior MUST produce clear logs and deterministic results for stock checks, selector detection, and alert delivery.

This principle keeps a fast-reacting project reliable and reduces false positives or missed restocks.

### IV. Single-User, Low-Noise Operation
The system MUST be designed for one user at a time, with explicit rate limits, jitter, and bounded retry behavior. It MUST avoid excessive traffic, noisy duplicate notifications, and broad parallelism unless intentionally configured.

This principle preserves respectful retailer interaction and keeps the tool practical for a personal use case rather than a high-volume bot.

### V. Explicit Retailer Compatibility
Each retailer watcher MUST be explicit about its assumptions: supported URLs, CSS selectors, and fallback response handling. The project MUST favor readable, site-specific logic over opaque generic heuristics and MUST document when selectors are likely to change.

This principle keeps retailer-specific logic reviewable and easier to debug when a site changes its markup.

## Operational Constraints

- The project MUST support Python 3.11+ and use a small set of explicit dependencies.
- Browser profiles and retailer sessions MUST be stored locally and left outside source control.
- Stock detection MUST default to a safe, conservative positive signal that requires a clear availability indicator before triggering alerts.
- Webhook or SMS alert delivery MUST be optional and provide a direct product URL in the notification payload.
- The project MUST document the difference between alert-only mode and assisted checkout mode and enforce a manual review step before final purchase submission.
- Any retailer-specific logic MUST be associated with the exact product URL and selector configuration for that site.

## Development Workflow

- Every bounded work item MUST begin with a feature specification and a reviewable implementation plan.
- Changes MUST be validated with the smallest relevant automated test suite before being considered complete.
- The repository MUST keep documentation and configuration examples aligned with the actual CLI behavior.
- Public-facing documentation MUST describe both expected runtime risks and the safety constraints that prevent unauthorized checkout automation.
- During implementation, the project MUST prefer small, independently testable components over large coupled flows.

## Governance

This constitution supersedes ad hoc workflow choices for this repository. Any change to the governance rules or the non-negotiable principles MUST be documented, reviewed, and versioned before being relied upon in implementation.

Implementation work MUST verify compliance with these rules before merge. The maintainers MUST treat privacy, user consent, and retailer compliance as first-class concerns, not as optional quality improvements. Complexity or performance shortcuts that weaken these principles are not permitted without an explicit governance update.

**Version**: 1.0.0 | **Ratified**: 2026-10-29 | **Last Amended**: 2026-10-29
