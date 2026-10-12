# T6 review 1: confirmation emails (pr-reviewer)

Branch `feat/T6-confirmation-emails`, reviewed read-only. No GitHub: this file is the review (protocol s12).

## What this means for the owner
Booking and cancel emails work as specified: one message per real booking or cancellation, none on refusals or repeats, and an email problem cannot undo a booking. Nothing leaves the app (it only writes messages down). No blockers. Three small follow-ups are listed; you need to do nothing now.

## Evidence
- Full suite (`-o addopts=''`): 286 passed. `tests/test_mail.py` run 8 more times: 37 passed each time, no flakes.
- Mutations in throwaway copies (nothing in the worktree changed):

| Mutation | Result |
|---|---|
| mailer exception allowed to propagate | caught (2 tests) |
| `NullMailer`-like no-op returned by `build_mailer` | caught (N-4 test) |
| control-character check removed from templates | caught (10 tests) |
| final `recorded/failed` update skipped | caught (3 tests) |
| user email added to the error log | caught |
| header-injection and "@" checks removed from RecordingMailer | caught |
| mailer called while a write transaction is held | caught (8 tests, via lock probe) |
| `ON CONFLICT ... DO NOTHING` removed | survives, but equivalent: the `UNIQUE (booking_id, kind)` insert then raises, is caught, logged, nothing sent. Behaviour is the same, only the log line differs |
| `_mail` made unconditional (`if True`) | survives, but equivalent today: refusal Results carry no email, so `render` rejects them and nothing is sent. `Result.changed` is the only deliberate guard |
| send made inline instead of `BackgroundTasks` | survives (see M-1) |
| user email appended to the message body | survives (see M-2) |

## Checklist
- AC-4b.1/4b.2: subject and body contain title, London time and "booked"/"cancelled" (`mail/templates.py:21-27`, test `test_mail.py:29-39`). The student's name is intentionally absent. AC-4b.1 requires title, date/time and "booked" only, so this is consistent with the spec, and it is what threat T-17 asks for (no attacker-chosen text to a victim). Accepted.
- AC-4b.3: failing mailer leaves booking, redirect and spots left unchanged, row `failed`, error logged with kind, booking id and exception type only (`outbox.py:22-33`, tests `:184-218`). The test would error if the exception escaped, because TestClient re-raises.
- AC-4b.4: refusals, no-ops, 404, CSRF failure, admin, anonymous send nothing (`:248-272`); the route queues only when `result.changed` (`routes/bookings.py:37-43`).
- AC-4b.5: duplicate request sends one (`:221-239`); the second is a service no-op, and the unique key is a second guard.
- AC-4b.6 and ADR-0004 gate: `build_mailer` only returns `RecordingMailer` and rejects other backends; config already refuses anything but `recording` (`config.py:96-97`), tested including the real start path. No real delivery path exists. The record is the `messages` row written by the outbox, so a future real mailer is still recorded without changing the rules.
- Capability email-and-notifications: sent from a background task after the response (not inside the request), deduped, plain text only, per-user cap (T5's 20/hour, test `:283`), odd titles kept verbatim, test environments cannot email anyone. Retry/alert and unsubscribe/links are not applicable in phase 1.
- Background task and locking: `BackgroundTasks` runs after the response is sent; the booking transaction has already committed and closed. The outbox uses three separate short transactions (pending row, mailer call with none open, status update), so the write lock is free during the send (proved by the `Spy` probe in `test_mail.py:100-110, 165-172`). Interleaving: two requests for the same (booking, kind) cannot both insert, and each updates only its own row by id, so the other cannot clobber it. Different bookings do not interact. A crash between insert and update leaves a visible `pending` row (accepted in ADR-0004).
- SQL is parameterised; logs carry no user data (test `:184-198`).

## Findings

### [BLOCKER]
None.

### [MAJOR]
None.

### [MINOR]
- M-1 `routes/bookings.py:37-43` and tests: nothing proves the send happens after the response rather than inline. Replacing `tasks.add_task(send_confirmation, ...)` with a direct call passes all 37 tests. The capability file says not to send inside the request and architecture s6 names `BackgroundTasks`. Add a test that observes ordering (for example the stub mailer records whether the response has already been started, via a tiny ASGI wrapper, or assert the route function returns a response whose `.background` is set). Not blocking because the lock and commit properties, which matter most, are tested.
- M-2 `tests/test_mail.py:29-39`: the T-17 decision (no student name) has no test; appending the user email or name to the body also passes. Add a test that renders with a distinctive name/email and asserts the body equals the expected exact text (or does not contain the name). The decision should be written down in ADR-0004 or the spec Change log so a later developer does not "improve" it back in.
- M-3 `mail/outbox.py:22-33` + `:36-40`: a lock timeout (`DatabaseBusy`) on the pending insert silently drops the email (logged), and a failed final update leaves `pending` forever. Acceptable under ADR-0004's crash trade-off, but there is no way to find such rows later. Record in STATUS.md that pending rows older than a few minutes are the signal, for the outbox upgrade.

### [NIT]
- N-1 `templates.py:21`: bidi override characters (category Cf, e.g. U+202E) pass the control-character check and the test asserts they are kept (`test_mail.py:42`). Harmless in plain text; just a conscious choice.
- N-2 `mail/__init__.py:14`: `RecordingMailer` records nothing itself (the outbox does). The docstring explains it; the name could mislead a reader.
- N-3 `routes/bookings.py:37`: `_mail` takes the kind as a string next to `result.changed`; deriving the kind from `result.outcome` would remove one way to pass the wrong one.
- N-4 Handoff open item 2: T4 must not mail on studio class cancel; the test simulates it only in SQL. T7's matrix should cover the real T4 route once merged.

### [QUESTION]
None.

### [PRAISE]
- P-1 Three short transactions with the mailer called between them, and `ON CONFLICT DO NOTHING` plus a unique key, is exactly the safe shape; the lock-probe `Spy` tests it for real.
- P-2 Error messages never echo the data, and the log test asserts the absence of the address and title.

## Not verified
No real server run (TestClient runs background tasks before returning); no CI exists.

## Handoff
```
HANDOFF
From: pr-reviewer            To: developer
Status: DONE
Summary: T6 reviewed independently; 286 tests pass, mail tests 8 more runs without flakes; 7 of 10 mutations caught, 2 survivors are equivalent today, 2 reveal test gaps (inline send, name/email in body); zero BLOCKER/MAJOR; 3 MINOR, 4 NIT.
Artifacts: .autocraft/work/T6/review-1.md
Open items: M-1 test that the send runs after the response; M-2 exact-body/no-name test and record the T-17 decision in ADR-0004 or the spec Change log; M-3 note in STATUS.md that stale `pending` rows are the outbox-upgrade signal; N-4 T7 to cover the real studio class-cancel route sends no mail.
Next: orchestrator records the MINORs and commits the review; human merges.
```

VERDICT: APPROVED
