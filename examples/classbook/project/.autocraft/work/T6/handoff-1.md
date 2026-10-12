# T6 handoff 1: confirmation emails

Branch `feat/T6-confirmation-emails` (from main with T1,T2,T3,T5). No GitHub: this file is the pull request (protocol s12).

## What and why
- `mail/__init__.py`: `RecordingMailer` replaces `NullMailer` (deleted) as what `build_mailer` returns (N-4). Its `send` refuses CR/LF/NUL in recipient/subject and a recipient without "@".
- `mail/templates.py`: `render(kind, to, title, starts_at) -> (subject, body)`; plain text, London time, "booked"/"cancelled"; control characters (incl. U+0085, U+2028) or an empty title raise `UnsafeMessage` (message never echoes data). The student's name is deliberately NOT used (T-17: attacker-chosen text to a victim).
- `mail/outbox.py`: `send_confirmation(...)` runs after the response: (1) own tx inserts `pending` row, `ON CONFLICT (booking_id, kind) DO NOTHING` (duplicate -> nothing sent); (2) mailer is called with no transaction open; (3) own tx sets `recorded` or `failed`. Never raises; logs only kind, booking id, exception type.
- `routes/bookings.py` (minimal): `BackgroundTasks` + `get_mailer`; `_mail()` queues the send only when `Result.changed`.
- Config already accepted only `MAIL_BACKEND=recording` (T1); tests added for the refusal incl. real start path.
- Cap: T5's 20 actions/hour/user already bounds mail; test proves 20 mails then 429 and no 21st.
- `tests/test_mail.py`: 37 tests, own fixtures (admin id 1 from bootstrap, students 2 and 3), no use of the T5 fixture.

## Verify
`$PY -m pytest` (full suite, no ignores). Result is in the final report.

## Choices / deviations
1. Mailer.send is the "delivery" step; the `messages` row (written by outbox) is the record, so RecordingMailer keeps no state of its own.
2. Message kinds: `booked`, `cancelled`. A re-booking is a new booking id, so it gets its own mail.
3. A `failed` row blocks a retry of the same (booking, kind) (known, ADR-0004 outbox upgrade).
4. If rendering is rejected (control chars) or the pending insert fails: error logged, no row, booking untouched. If the final status update fails the row stays `pending` (visible).
5. Mail is queued also for the route path only; NOT_FOUND raises 404 before queueing; refusals/no-ops are not `changed`.
6. Class cancel by the studio (T4 route, not present) sends nothing; simulated in SQL in a test. T4 must not call the mailer.
7. Failure test stubs the mailer on `app.state.mailer`.

## Not done
No real-server run (TestClient runs background tasks before returning). `docs` untouched.

HANDOFF
From: developer            To: pr-reviewer
Status: DONE
Summary: T6 confirmation emails: RecordingMailer (NullMailer removed, N-4 test), plain-text templates, pending->recorded/failed best-effort after commit with unique-guard dedupe, wired into the book/cancel routes with minimal edits. 37 new tests.
Artifacts: branch feat/T6-confirmation-emails; .autocraft/work/T6/handoff-1.md
Open items: 1. Choices 3 and 4 above. 2. T4 must not mail on studio class cancel. 3. No real-server run.
Next: review per protocol s12; write .autocraft/work/T6/review-1.md with a VERDICT line. Human merges.
