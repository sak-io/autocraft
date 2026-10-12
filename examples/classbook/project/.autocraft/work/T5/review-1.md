# T5 review 1: booking and cancellation core (pr-reviewer)

Branch `feat/T5-booking`, reviewed read-only in the worktree. No GitHub: this file is the review (protocol s12).

## What this means for the owner
The booking and cancel code is correct and well tested. Nothing blocks it. A few small tidy-ups are listed as MINOR; none needs to happen before you merge, but two should be recorded for T6/T7. You do not need to do anything now.

## Evidence I produced
- Full suite: 197 passed. `tests/test_bookings.py` run 10 more times: 35 passed every time, no flakes.
- Mutation checks (throwaway copies under scratchpad, nothing in the worktree changed):

| Mutation | Caught by |
|---|---|
| `BEGIN IMMEDIATE` -> plain `BEGIN` in `kernel/db.py` | 10 tests fail: all 4 probe-clock tests, 50-on-1, 30-on-10, double submit, book-vs-cancel, parallel cancels, parallel HTTP |
| cap `>=` -> `>` | `test_http_throttle_returns_429_with_retry_after` |
| cancel without `b.user_id = ?` | `test_student_a_cannot_see_or_cancel_student_bs_booking` |
| spots check weakened | race tests |
| "already booked" check removed | `test_same_student_double_submit_in_parallel...` |
| day-30 `<=` -> `<` | `test_window_boundaries...` |
| 12 h `>=` -> `>` | `test_cancel_exactly_12h...` |
| "already cancelled" check removed | `test_parallel_cancels...` |
| cap window filter removed | `test_concurrent_http_requests...` |

So the race tests really do depend on the lock; they are not passing by luck of the unique index `bookings_one_active`.

## Checklist results
1. Task and ACs: book, my bookings (incl. studio-cancelled greyed), cancel, cap, Result for the mail hook. Nothing extra. OK.
2. Rule order against api.md #6/#8, checked in code and tests:
   - Book: unknown 404 -> started/cancelled -> too far ahead (with opens-on) -> already booked (no-op) -> full. Matches (`services/bookings.py:74-88`). Tests cover each overlapping pair (`test_bookings.py:48-76`: started+full+already, too-far+already+full, already+full).
   - Cancel: not found/not mine 404 -> already cancelled no-op (includes studio-cancelled) -> too late (<12 h or started). Matches (`:108-115`), tested at `:93-129`.
   - Boundaries: day 30 booked, +1 s refused; exactly 12 h cancelled, 12 h - 1 s refused (`:79-84`, `:107-111`). Both use the kernel predicates only.
3. Idempotency: double book creates no second row (unique index plus the check, tested serially and with 10 parallel submits); double cancel changes once (the UPDATE also has `AND status='booked'`); spot freed once. OK.
4. Cap (20/hour/user): refusals count (20 x unknown-class then 21st throttled); throttled attempt is not recorded (count stays 20); per user; shared by book and cancel; rolling window with exact boundary (59 m 59 s throttled, 1 h allowed). The `user_actions` row commits with a refusal because refusals are returns, not exceptions, so `write_tx` commits; the 404 is raised by the route after the commit. OK.
5. `now`: read once, first statement inside `write_tx` (`:71`, `:100`); `ProbeClock` proves exactly one call while a second connection cannot get the lock, for book, cancel and both refusal paths. M-4 is handled in the service. OK.
6. Spots left: derived by `rules.spots_left` (COUNT), never stored; cannot go negative because check and insert are under `BEGIN IMMEDIATE`. Tests assert exact winner counts. OK.
7. AuthZ: ownership is in the SQL (`b.user_id = ?`), user id comes from the session only; A cannot cancel or see B's booking (404, unchanged); admin 403 and anonymous 303 via `require_student`; missing CSRF token 403 (tested). OK.
8. Mail: the service has no mailer. `Result` is returned only after `with write_tx` exits, i.e. after COMMIT, and `changed` is true only for BOOKED/CANCELLED. If COMMIT raised, no Result would exist. OK for T6.
9. SQL: all values are bound parameters; the only f-string SQL is the constant in `kernel/rules.py`. OK. Templates autoescape; XSS test present.

## Findings

### [BLOCKER]
None.

### [MAJOR]
None.

### [MINOR]
- M-1 `services/bookings.py:72,101` vs `docs/architecture/api.md` row 6: api.md lists "404 unknown" as the first check and says "Also 429"; the code checks the cap before the 404. The developer declared this (handoff choice 1) and it is sensible (probing ids is rate limited and the 404 counts), but it is a deviation from the source of truth. Add one line to api.md (and the spec Change log) saying "the 20/hour cap is checked first and counts every attempt that passes it". Track for the orchestrator; no code change.
- M-2 `tests/test_web_shell.py:281`: removing `assert all(r.routes == [] ...)` is acceptable (T3, T4, T5 each make it false by design, and the registration assert stays). But the test now says less than before. Suggest, when the last of T3/T4/T5 lands, replacing it with "every router has at least one route" so an accidentally empty router is still caught. Track for whoever merges the third of the three.
- M-3 No test for the lock-timeout path on the new routes (`DatabaseBusy` -> 503 exists in `app.py:34`, but nothing proves `POST /classes/{id}/book` returns 503 and creates nothing/no cap row). Cheap to add (hold `BEGIN IMMEDIATE` on another connection with a small busy timeout). T7 may cover it; please record that.
- M-4 Carry-over from T1: `now` is read correctly here by convention only. The kernel could yield `(conn, now)` so T6/T7 and later code cannot get it wrong. Not required now; keep it in the follow-up list.

### [NIT]
- N-1 `tests/test_bookings.py:341-345` the HTTP cap test only uses a 404 class; one HTTP case where a 409 refusal also counts would show the commit-on-refusal path through the route (the service-level test already proves it).
- N-2 `services/bookings.py:87` `spots_left` can return None for an unknown class; unreachable here because the class was just loaded under the lock, but `<= 0` on None would raise. A one-word comment would help the next reader.
- N-3 `routes/bookings.py:13` the alias `O = Outcome` is terse; `Outcome` spelled out reads better. Taste only.

### [QUESTION]
None.

### [PRAISE]
- P-1 Refusals as return values so the cap row commits with them, and a single `Result` that carries exactly what T6 needs, is a clean design.
- P-2 The probe-clock test is a real, behaviour-level proof of M-4, and the thread tests assert exact counts and use their own connections.

## Not verified
- No real uvicorn or browser run (TestClient only); the real-HTTP race is T7's.
- No CI exists (no GitHub); local runs only.

## Handoff
```
HANDOFF
From: pr-reviewer            To: developer
Status: DONE
Summary: T5 reviewed independently; 197 tests pass, booking tests 10 more runs with no flakes; 9 mutations (incl. BEGIN IMMEDIATE -> BEGIN) all caught; zero BLOCKER/MAJOR; 4 MINOR, 3 NIT.
Artifacts: .autocraft/work/T5/review-1.md
Open items: M-1 add the cap-first line to api.md / spec Change log (orchestrator); M-2 tighten the router assertion once T3/T4/T5 are all merged; M-3 add a 503-on-lock-timeout test for the book/cancel routes (or record for T7); M-4 kernel yielding `now` stays a follow-up.
Next: orchestrator records the MINORs in docs/STATUS.md and commits the review; human merges.
```

VERDICT: APPROVED
