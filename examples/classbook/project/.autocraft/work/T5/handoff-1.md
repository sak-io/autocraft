# T5 handoff 1: booking and cancellation core

Branch `feat/T5-booking` (from main, contains T1 + T2). No GitHub: this file is the pull request (protocol s12).
Covers work-breakdown row T5 and follow-ups F24 (user_actions cap) and M-4 (`now` after the lock).

## What and why
- `classbook/services/bookings.py` (new): `book()`, `cancel()`, `upcoming_for()`. Each does ONE `write_tx`, reads `now` once inside it, and RETURNS a `Result` (outcome enum, booking/class ids, title, starts_at, user email/name, `opens_at`, `changed`). `Result.changed` is true only for BOOKED / CANCELLED, so T6 sends mail after commit only then. Refusals are returns, not exceptions, so the `user_actions` row commits with the refusal (F24: refusals count).
- Order. Book: cap -> unknown (404) -> cancelled/started -> too far ahead (with `opens_at`) -> already booked (no-op) -> full. Cancel: cap -> not found or not mine (404) -> already cancelled (no-op, includes studio-cancelled) -> too late (<12h or started). Uses kernel `is_bookable`, `opens_at`, `cancel_allowed`, `spots_left`; no rule re-implemented.
- `classbook/routes/bookings.py`: `POST /classes/{id}/book`, `GET /my-bookings`, `POST /bookings/{id}/cancel`, all behind `require_student` (admin 403, anonymous 303 to login). 404 via HTTPException, refusals render `bookings/refused.html` with 409 (429 plus `Retry-After: 3600` for the cap), success is a 303 to `/my-bookings` with a flash.
- Templates only under `classbook/web/templates/bookings/` (`my_bookings.html`, `refused.html`); cancel form uses `csrf_field()`.
- `tests/test_bookings.py`: 35 tests.

## How to verify
```
PY=/tmp/claude-0/-home-user-autocraft/4dc487e6-d297-5355-ab6e-8239135c933c/scratchpad/venv/bin/python
cd /tmp/claude-0/-home-user-autocraft/4dc487e6-d297-5355-ab6e-8239135c933c/scratchpad/wt-T5
$PY -m pytest ; $PY -m compileall -q classbook tests
```
Test evidence (whole suite): `197 passed, 1 warning in 5.61s` (162 existing + 35 new; the warning is the known starlette/httpx TestClient deprecation). `tests/test_bookings.py` alone was run 5 times with no flakes.

What the tests prove: rule order with overlapping conditions (every pair that could be ambiguous), day-30 and +1 s, exactly 12 h and 1 s less, no-op cases, rebooking inserts a new row, mail-hook data in `Result`; `now` read exactly once and only while the write lock is held (a probe clock tries `BEGIN IMMEDIATE` on a second connection with zero timeout); cap (20 allowed, 21st throttled, refusals count, shared by book and cancel, per user, rolls after exactly 1 h); HTTP: CSRF 403, each refusal, admin 403, anonymous 303, A cannot see or cancel B's booking (404, unchanged), studio-cancelled shown greyed with no cancel button, student-cancelled and past hidden, XSS escaping; concurrency with real threads and own connections: 50 on 1 spot (exactly one wins), 30 on 10 spots (exactly 10), same student 10 parallel submits (one booking), book vs cancel race, 10 parallel cancels (spot freed once), 8 parallel HTTP posts.

## Choices where the architecture was silent / deviations
1. **Cap is checked first**, before the 404, and counts every attempt that passes it (including 404s). A throttled attempt is NOT recorded, so a blocked user is unblocked exactly 1 h after their 20th-oldest action instead of the window being extended by retries. Window is rolling: `at > now - 1h`.
2. **`now` and the kernel.** I did not change `write_tx`. `clock.now()` is called as the first statement inside the `with write_tx(...)` body (after `BEGIN IMMEDIATE`). Suggestion for later: the kernel could yield `now` (M-4) so no caller can get this wrong; then these two lines become `conn, now`.
3. `Result` also carries `now` and, for TOO_FAR_AHEAD, `opens_at`; the route formats it in London time.
4. Admin is stopped by the `require_student` guard (403) before the service runs, so an admin attempt records no action.
5. `GET /my-bookings` "upcoming" = class `starts_at > now`; it uses a plain read connection and the same `get_clock()` (one `now` per request, no lock needed for a read).
6. A booking of an upcoming class that was cancelled by the studio shows greyed "Cancelled by the studio"; a booked one within 12 h shows "Too late to cancel online" instead of a button (the server still enforces it).
7. **Edit outside my files (minimal):** `tests/test_web_shell.py::test_empty_routers_are_registered_by_the_factory` asserted all routers are empty; I removed only that last assert line (the registration assert stays). T3/T4 will hit the same line; merge conflicts there are trivial (delete the line).
8. Messages (flash and refusal pages) are plain English; the exact wording is mine and can be tuned.

## Not done / not run
- Mail hook is not wired (T6): routes ignore `Result.changed` for now; the mailer/BackgroundTasks call goes in the two routes after the service call.
- No real uvicorn or browser run (TestClient only). The real-HTTP race is T7's.
- Nav links and `/classes/{id}` Book button belong to T4; the Book POST was tested only by direct POST.
- CSS for `.bookings` list is not added (base styles only), to avoid editing the shared stylesheet.

HANDOFF
From: developer            To: pr-reviewer
Status: DONE
Summary: T5 booking core: services/bookings (book, cancel, upcoming) returning Result for the T6 mail hook, three routes, templates under web/templates/bookings, 20/hour cap via user_actions, `now` read once inside the lock. 197 tests pass (35 new, incl. 50-thread and 30-on-10 races).
Artifacts: branch feat/T5-booking; .autocraft/work/T5/handoff-1.md
Open items: 1. Cap checked before 404 and throttled attempts not recorded (choice 1). 2. Kernel could yield `now` (choice 2). 3. One-line edit to test_web_shell.py (choice 7). 4. No real-browser check.
Next: review per protocol s12; write .autocraft/work/T5/review-1.md with a VERDICT line. Human merges.
