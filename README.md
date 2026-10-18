# ajax-ticket-watch

Read-only Ajax ticket monitoring in Python + Playwright. No purchases, reservations or CAPTCHA bypass.

## Current result

The hosted GitHub runner receives HTTP 403 from CloudFront.
A diagnostic using official Chrome in both headed and headless modes reached captcha-delivery.com/captcha.
The response explicitly contained a CAPTCHA delivery script. Therefore no more automatic cloud attempts are useful without human verification.
The ordinary Ajax password login page was also denied before any credentials were entered.
Cloud email alerts are NOT operational.

The signed-in user's Chrome opened Ajax–ADO Den Haag (22 November 2026, 14:30).
The observed regular category 405 406 420 421 (low), EUR 52, offered quantities 0 and 1.
This did not meet the threshold of two.

## Local Mac edition

The local alternative keeps a dedicated Chrome login profile on the Mac and pauses for manual verification when necessary.
It does not route traffic through a proxy or attempt to solve a CAPTCHA.

1. Download the Mac ZIP from Releases, extract the entire folder and open run-local.command.
2. Requires Google Chrome and Python 3.10 or newer. If Python is missing the launcher opens the official Python download page.
3. Enter your sending Gmail and intended recipient.
4. Enter a Gmail app password in the hidden prompt. It is stored only in macOS Keychain.
5. A setup email is clearly labeled as a test and does not claim tickets were found.
6. Sign in manually in the dedicated Chrome window and open the event table; then press Enter in Terminal.
7. Keep Terminal and Chrome open. Checks run every five minutes. The launcher prevents idle sleep while running; closing the laptop or losing internet interrupts checks. Ctrl+C stops it.

Profile, mail configuration and deduplication state stay beneath:
~/Library/Application Support/ajax-ticket-watch

Private files use restrictive permissions. No local session or Keychain secret is uploaded.
Only one local watcher may run at a time.
Uninstall by stopping the watcher and removing its private Application Support folder; the SMTP app password remains in Keychain until the user removes it.

## Availability rules and limitations

- Reads enabled quantity options from the inspected best-available-seat table.
- At least two eligible tickets are required.
- Counts distinct seat categories; multiple tariffs in the same category count only their maximum.
- Regulier, Regular and Official Resale labels are allowed.
- VIP, Premium, Hospitality, Business and Skybox rows are excluded.
- Unknown rates and layouts never imply availability.
- Official Resale parsing has synthetic regression coverage, but a live resale offer has not yet been observed. Other resale layouts may need an adapter update.
- Alerts describe a quantity-control indication, not checkout confirmation or reserved seats.
- Identical offer fingerprints are not resent. Changes may generate a new alert.
- SMTP delivery and state writes are not transactional: a crash after delivery can cause a repeat.

## Verification and packaging

The manual package workflow checks Python and shell syntax and runs offline Chromium regression cases before publishing a ZIP.
The tests cover the observed one-ticket state, two tickets, distinct categories, shared category inventory, Official Resale labels, exclusions, disabled controls, unknown rates, wrong events and HTTP 403.
These tests do not establish live Mac compatibility or live email delivery. Those remain to be verified on the user's Mac.

## Original GitHub Actions workflow

watch.yml requests a run every five minutes, with concurrency and state commits.
GitHub may delay or drop schedules. Hosted cloud access is currently blocked as described above.
Encrypted Ajax credentials are configured but not validated, since the access refusal precedes credential entry.
SMTP settings are intentionally not collected while hosted access is blocked.
