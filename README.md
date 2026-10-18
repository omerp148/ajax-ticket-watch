# ajax-ticket-watch

Python + Playwright, with GitHub Actions scheduled every five minutes.

## Current deployment status

Infrastructure deployed; availability detection is NOT yet verified.
On 2026-10-18 the supplied event URL showed "Unfortunately, the requested URL was not found on this server". Continue shopping led to Ajax sign-in.
No seat selectors are fabricated. Until the event can be inspected and selectors.json verified, runs fail closed with a clear status and cannot send a ticket alert. Error pages do not mean sold out.

## Behavior

- Read-only: no seat clicks, reservations, purchases, CAPTCHA solving or bypass.
- At least two distinct available regular seat IDs required.
- Explicit regular / Official Resale type allowlist; VIP, Premium, Hospitality, Business and Skybox excluded.
- Unknown layouts, access blocks and login pages fail instead of reporting availability.
- state.json persists observations and successfully notified seat sets.
- Workflow concurrency prevents overlapping monitors.
- Email delivery precedes recording the notification. SMTP delivery and Git persistence are not transactional: a crash between them can cause a repeated email.

## Secure configuration

Repository Settings > Secrets and variables > Actions:
SMTP_HOST (e.g. smtp.gmail.com), SMTP_USER, SMTP_PASSWORD (provider app password, never normal account password), MAIL_FROM, MAIL_TO.
Recipient is configured privately through MAIL_TO.
No credentials, session cookies or browser storage should be committed to this public repository.

A verified selectors.json adapter must identify event_root, ticket_row, ticket_type, allowed_types, available_marker and seat_id_attribute, plus verified_event = 10229728133611. Validate with rendered real event examples before enabling alerts. Login sessions are not currently exported or persisted.

## Scheduling and cost

Uses standard ubuntu-latest runners in a public repository. No paid service is configured.
The cron expression requests every five minutes; GitHub may delay or drop scheduled runs and may disable schedules after prolonged repository inactivity. This is not a guaranteed five-minute SLA.

## Validation

Each run compiles monitor.py before launching Chromium. See Actions for live run status and the observation summary. Email delivery remains untested until SMTP configuration is supplied.
