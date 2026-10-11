# ADR 0004: Replaceable mailer, sent best-effort after commit

- **Status:** Accepted  ·  **Date:** 2026-10-10

## Context
Confirmation emails (US-4b) must never fail a booking (AC-4b.3), must not duplicate (AC-4b.5), and no real mail service exists now (AC-4b.6).

## Decision
Define `Mailer.send(to, subject, body)`. Phase 1 ships `RecordingMailer`, which inserts into the `messages` table. Services call the mailer only after the booking/cancellation transaction commits, inside try/except, through FastAPI `BackgroundTasks`; a failure marks the message `failed` and logs it. The email is triggered only by the code path that actually created/cancelled a row, plus a unique `(booking_id, kind)` constraint as a second guard. In phase 1 the config accepts only `MAIL_BACKEND=recording` (anything else refuses to start). Flow: after commit the service inserts a `messages` row `pending`, the mailer sends, the row becomes `recorded` or `failed`. Control characters are rejected in name/title/instructor; book/cancel actions are capped at 20 per hour per user. **Gate: real delivery must not be enabled until sign-up email verification exists**, because anyone can currently sign up with someone else's address and the confirmation would reach that person.

## Alternatives considered
1. Send inside the booking transaction – a mail error or slow provider would roll back or block bookings; violates AC-4b.3.
2. Outbox table + background worker with retries – the right design for real delivery, but extra moving part with nothing real to deliver; adopt when a provider is connected.

## Consequences
A crash between commit and send loses one email (acceptable, logged state is consistent). The outbox upgrade (retries, and handling the unique `(booking_id, kind)` constraint blocking a retry after `failed`) is a contained change behind the same interface.
