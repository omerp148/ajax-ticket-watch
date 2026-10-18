# ajax-ticket-watch

Python and Playwright monitor, scheduled every five minutes through GitHub Actions.

## Live deployment status — 2026-10-18

The signed-in Chrome session successfully opened Ajax–ADO Den Haag, 22 November 2026 at 14:30.
The best-available-seat table showed Regulier, category 405 406 420 421 (low), EUR 52, with quantity options 0 and 1. This is below the alert threshold.
The table URL and DOM selectors were inspected on the real event.
A clean GitHub runner returned HTTP 403. The local Chrome sign-in is not shared with GitHub.
Normal email/password Ajax login support is implemented but untested until encrypted Ajax credentials are supplied. It may still be blocked or require interactive verification.
Email delivery is not active or tested until SMTP secrets are supplied. This is not yet an operational end-to-end ticket alert service.

## Behavior

- No seat selection, cart additions, reservations, purchases, or CAPTCHA solving/bypass.
- Counts enabled quantity options in the actual best-available-seat table.
- Distinct categories are summed; multiple tariffs within one category count only their maximum to avoid overlap.
- Only Regulier, Regular and Official Resale rate labels are allowlisted.
- VIP, Premium, Hospitality, Business and Skybox rows are excluded.
- Official Resale label support has not yet been verified against a live resale offer. Other resale layouts fail closed or are ignored rather than guessed.
- Availability alerts are indications from quantity controls, not checkout confirmation.
- Unknown pages, 403, login failures and changed layouts fail with an explicit status.
- state.json persists observed offers and notified fingerprints. Repeated identical offers do not resend.
- SMTP delivery and Git commits are not transactional: a crash or commit failure after mail delivery can cause a repeat.
- Changes in offers can generate a new notification, even when some categories overlap.

## Encrypted GitHub Actions secrets

| Secret | Value |
| --- | --- |
| AJAX_EMAIL | Ajax email for ordinary email/password sign-in |
| AJAX_PASSWORD | Ajax password; never a Google/Apple/Facebook password |
| SMTP_USER | Sending Gmail address |
| SMTP_PASSWORD | Gmail app password |
| MAIL_TO | Recipient, already configured privately |
| SMTP_HOST | Optional; defaults to smtp.gmail.com |
| MAIL_FROM | Optional; defaults to SMTP_USER |
| AJAX_STORAGE_STATE | Optional Playwright session JSON, only through a secret |

Never commit credentials or browser storage to this public repository.
Login attempts stop on CAPTCHA, access denial, failed credentials or interactive verification. No automatic retries of failed credentials.
Social login and interactive MFA are not automated. Credentials might not resolve GitHub's 403 access denial.

## Scheduling and cost

Uses standard ubuntu-latest runners in a public repository. No paid service configured.
Cron requests every five minutes; GitHub may delay/drop runs or disable schedules after prolonged inactivity.
The machine running Chrome does not need to remain online if the GitHub runner eventually obtains access.

## Verification

Each workflow compiles monitor.py before launching Chromium.
The current live runner result and observation appear in Actions.
A successful authenticated run and email delivery test are still required before claiming the service is working.
