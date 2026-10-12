# ClassBook QA summary (T7, cross-task assurance)

Branch `test/T7-cross-task-assurance` (from `main` = T1-T6 integrated). QA engineer did not write the code under test.
Plan: `docs/qa/test-plan.md`. Acceptance criteria to tests: `docs/qa/traceability.md`.

## What this means for you (Maya)
ClassBook does what the spec promises. I could not make it double-book a class, show one student another student's
bookings, let a student into the admin pages, or send an email it should not send. I found **no blockers and no
major defects**; I found **9 small defects** (all MINOR), written up below. None loses data or money. You do not need
to do anything now: they are for a developer to fix, and I suggest fixing D-1, D-3, D-5 and D-7 before the studio
uses it. Two things need a person with a phone and a keyboard (checklist at the end).

## Numbers
- Full run: **521 passed, 14 xfailed** (the 14 are the 9 open defects, written as tests that fail today on purpose),
  about 65 seconds. Before T7: 344 passed. New: 177 passing tests plus 14 defect-reproducing tests.
- Three consecutive full runs were identical (no flaky test); the real-HTTP tests were also run alone three more times.
- Real server (separate `uvicorn` process): 50 simultaneous bookings on 1 spot gave exactly 1 booking and 49 "Class is
  full"; 30 on 10 spots gave exactly 10; 12 parallel double-clicks gave 1 booking and 1 email. 30 simultaneous bookings:
  median 0.18 s, **p95 0.36 s**, max 0.55 s (spec: p95 under 1 s).
- 21 mutation probes (deliberate wrong changes to a copy of the code): **21 caught, 0 survived**
  (`python tests/qa/mutation_probes.py`).

## Criteria covered / not covered
- All 34 acceptance criteria (AC-1.1 to AC-6.4 including AC-4b.1 to 4b.6), the three change-log items and the answered
  questions that change behaviour have named tests: see `docs/qa/traceability.md`. **No AC is without a real test.**
- One AC is only partly met by the build: **AC-1.1** says greyed classes also show "spots left" (D-8).
- Not testable by software and therefore not covered: real browsers and phones (rendering, focus ring really visible,
  tap comfort), screen readers, real slow networks, real HTTPS in a browser (`__Host-` cookies), the Docker image and
  the CI workflow (no Docker or GitHub here), the proxy hop count on Render (T8 smoke checklist F23), real email (none
  exists in phase 1), T8 items (backup, restore, monitor).

## What T7 added
| Scope item | Result |
|---|---|
| (2) Route guards | `tests/qa/test_route_guards.py`: every route (18, plus static files) is in a declared guard table; the only unguarded route is `GET /health`; admin paths demand the admin guard; a self-test proves the enumeration notices an unguarded route; `api.md` and the code list the same routes (only `GET /admin/backup`, T8, is documented but not built); no `/docs`, `/redoc`, `/openapi.json`. Every router has routes (T5 follow-up). |
| (2) Authz matrix | `tests/qa/test_authz_matrix.py`: 18 routes x {anonymous, student A (owner), student B, admin} = 72 cells with exact status and redirect target, "refused means the database did not change" and "refusal pages leak no names or emails"; CSRF missing/wrong/header-only on every POST for every role (96 checks); PUT/PATCH/DELETE on every path give 405 and change nothing; booking-id guessing (foreign and non-existent look identical, cap stops a sweep); roster visible only to the admin. |
| (3) Race over real HTTP | `tests/e2e/test_booking_race_http.py` (see Numbers), plus cancel vs 19 bookers and studio class-cancel vs 20 bookers: no `booked` row survives on a cancelled class, no mail for it. Server log checked for crashes. |
| (4) Journey over real HTTP | `tests/e2e/test_journey_http.py`: visitor -> schedule (greyed, hidden classes) -> class page -> sign in with `next` -> book -> My bookings -> double-click -> cancel -> cancel again -> rebook -> sign out -> admin roster -> admin cancels class -> student sees "cancelled by the studio" -> messages table: booked, cancelled, booked and nothing for the studio cancel. The server log is searched for passwords, emails and names: none. Also sign-up with `next`, and production mode (`__Host-` cookies, `Secure`, HSTS) over real HTTP. |
| (5) Accessibility | `tests/qa/test_accessibility.py`: 25 page states (visitor, student, admin, errors, 429s) checked for language, title, exactly one `h1`, heading order, unique ids, labelled inputs, skip link, named buttons/links, table scopes, responsive viewport that allows zoom; error and throttle pages in plain words with `Retry-After`; four bare pages (503, form expired, too large, crash) readable; focus ring on every control and never removed; skip link appears on focus; text contrast >= 4.5:1 in both themes for every text colour; 44 px tap targets. |
| (6) Review follow-ups | `tests/qa/test_followups.py`: mail is sent after the response is complete (T6 M-1); no student name/email in subject or body (T6 M-2); scrypt N=2^14, r=8, p=1, 32-byte output and `scrypt1$salt$hash` format pinned against an independent recomputation; exactly one scrypt per login in all three cases and none ever inside a write transaction (sign-up, log-in, admin bootstrap incl. reset); 129 to 5000 character passwords never crash log-in or sign-up; every write route (book, cancel, admin create/update/cancel, sign-up, log-in, log-out) answers 503 with `Retry-After`, writes nothing, and the app recovers; read pages keep working while a writer holds the lock; the real studio class-cancel route sends no mail, even clicked twice. |
| (7) Exploratory | `tests/qa/test_exploratory.py`, `tests/e2e/test_live_exploratory.py`: opening instant (1 s before / at), cancel cut-off (12 h +/- 1 s), a class starting this second, day 30 / 60 edges, session expiry at exactly 14 days, an old form after the session expired, SQL-looking text, emoji / right-to-left / combining text through page, flash cookie and email, extra form fields (`user_id`, `role=admin`, `status`), the admin's own email at sign-up, stale Book/Cancel buttons after a studio cancel, two tabs, logout in one tab, back-button (`no-store` on every signed-in page), garbage and oversize HTTP (11 kinds, all 4xx or closed, never 5xx), restart persistence, 8 parallel sign-ups of one email, lockout per email. |

## DEFECTS FOUND
All are MINOR. Each has a strict `xfail` test (`pytest -rx` lists them); when a developer fixes one, that test turns
into "unexpectedly passed" and fails the build until the `xfail` marker is removed, which makes it the regression test.

| ID | Severity | Summary |
|---|---|---|
| D-1 | MINOR | A signed-in student can make the server answer **500** with `POST /classes/99999999999999999999999/book` or `/bookings/99999999999999999999999/cancel` (id larger than 64 bits). api.md: unknown ids are 404. T4's fix (m-1) covered the class pages, not `services/bookings.py`. |
| D-2 | MINOR | Non-numeric ids (`/classes/abc`, `/admin/classes/abc` as admin, `POST /bookings/1.5/cancel`) return FastAPI's raw **JSON 422** instead of the 404 page. |
| D-3 | MINOR (ops) | `HEAD /health` answers **405**. Uptime monitors (T8 plans a free one) and some load balancers use HEAD and would report the studio as down. `GET` works. |
| D-4 | MINOR (carried from T3 review) | `dummy_hash()` is built lazily, so the first unknown-email login after each start pays two scrypts: measured 95 ms against 52 ms for a wrong password (one-time signal that an email is unknown). Fix: call it once in `create_app`. |
| D-5 | MINOR | The four bare pages (503 busy, 403 "form expired", 413, 500) have no viewport meta and no stylesheet: tiny text on a phone. "Form expired" is the one a student can really meet (idle too long). |
| D-6 | MINOR (confirm on a phone) | `style.css` has no `overflow-wrap`/`word-break`: an unbroken 80-character student name or 100-character class title (both allowed) or a long email in the roster makes the page scroll sideways on a 360 px screen. |
| D-7 | MINOR (security visibility) | The admin page shows the previous sign-in time but **not the count of failed attempts since**, which architecture s5/F29 and the AR-1 mitigation promise. `auth.service.last_sign_in()` computes it but nothing calls it. Password guessing against Maya's account is invisible. |
| D-8 | MINOR (spec vs build; owner may amend the spec) | AC-1.1 says every listed class, greyed ones included, shows "spots left"; the greyed rows show only "Opens for booking on ...". |
| D-9 | MINOR | On an unknown URL or a method error (404, 405), a signed-in student sees the signed-OUT menu ("Sign in / Sign up"), because the user is only looked up on guarded routes. |

Reproduction (all in-process, deterministic): `python -m pytest -o addopts='' -rx tests/qa tests/e2e`, then read each
`reason=`. Manual repro for D-1: sign in as any student, then `curl -b "session=<cookie>; csrf=T..." -d "csrf_token=T..." http://localhost:8000/classes/99999999999999999999999/book` (token = any 43 characters, same in cookie and field): the page says "Something went wrong" and the log shows `unhandled exception OverflowError`. D-3: `curl -I http://localhost:8000/health` -> `405`.

## Observations (not defects; for the owner or for T8)
- O-1 A 128-character password also accepts anything typed after character 128 (login truncates to 128). Harmless in practice.
- O-2 "30 days" is 720 hours, shown in London time: for a class just after the clocks go forward, the label's clock time
  is one hour earlier than the class time (class Sun 28 Mar 2027 11:00 BST opens Fri 26 Feb 10:00 GMT). This follows
  architecture s3 and the booking rule; Maya should confirm she is happy with "720 hours" rather than "same time, 30 days earlier". Pinned by a test.
- O-3 Sign-up throttle is 10 attempts per hour **per network address, counting typos**. Students sharing the studio Wi-Fi
  or one mobile carrier address can lock each other out of sign-up on a busy day ("Too many attempts"). Booking/login are unaffected. Consider 30 per hour or counting only completed sign-ups.
- O-4 Small input looseness: names of only zero-width characters, a password of ten spaces, and email addresses with commas,
  quotes or angle brackets pass validation. Harmless now (nothing is delivered), but **tighten the email check before real
  email delivery is ever connected** (ADR-0004 gate, threat T-17).
- O-5 Signing up while already signed in leaves the previous session alive in the database (the cookie is replaced).
  Passwords typed with composed vs decomposed accents (NFC/NFD) do not match each other. Both are low-risk.
- O-6 `GET /classes/1/` (trailing slash) redirects with an absolute `http://` URL; behind the host's HTTPS proxy the browser is
  upgraded again by HSTS/the host. Cosmetic.
- O-7 Still open from earlier reviews, not code: api.md row 6 / spec do not yet say "the 20-per-hour cap is checked before the
  404" (T5 M-1); decide what happens to bookings of a promoted student (T3, T8 runbook); stale `pending` rows in `messages`
  are the signal that an email was lost (T6 M-3, T8 runbook); Render disk write permission for the non-root user (T1 Q-1);
  CI, Docker build and pins are unproven until the first push (T1 M-1 to M-3).

## Residual risk
1. Everything here ran on Linux with an HTTP client; **no real browser, phone or screen reader** was used. Automated
   accessibility checks find roughly a third of problems. The manual checklist below closes the rest.
2. The hosting proxy, TLS, Render's disk, the nightly backup and restore are T8 and untested.
3. Single instance and SQLite: fine for the stated load (measured p95 0.36 s with 30 simultaneous bookers on this machine; a
   cheap host may be slower, so measure once after deploy).
4. The booking cap (20 actions per hour per student) and sign-up cap (O-3) are deliberate but could surprise real users.
5. Real email is not connected; its risks (verification, address validation) are deferred by ADR-0004 and not tested.
6. A time-of-day dependency exists only in the real-HTTP tests (classes are created 3, 45 or 75 days from the real clock, so they are stable for years, but not time-travel tests); the clock-edge tests use a fixed clock.

## Manual keyboard and phone checklist (about 15 minutes, once before opening to students)
Use the real site (or `uvicorn` locally) in a normal browser, then on your own phone.
Keyboard only (no mouse): press Tab from the top of the page.
1. First Tab shows "Skip to content"; Enter jumps past the menu.
2. Every link, button and field shows a clear outline when it has focus; you can always tell where you are.
3. Sign up and sign in using only Tab, Shift+Tab, Enter and typing. Wrong password shows a clear message.
4. Book a class, then cancel it, with the keyboard only. The confirmation message is visible after each step.
5. As admin: add a class with the keyboard only (the date/time field works with arrow keys); lower the capacity below the bookings and read the message.
Phone (portrait, then landscape):
6. Schedule readable without sideways scrolling or pinch-zoom; greyed "Opens for booking on ..." text is readable in sunlight.
7. Buttons and links are easy to tap with a thumb (no mis-taps); the menu wraps neatly.
8. Create an account with a very long name (80 letters, no spaces) and book a class; open the admin roster: does the page scroll sideways (D-6)?
9. Leave a class page open for an hour with the screen locked, then tap Book: you should see "This form has expired" in readable size (D-5).
10. Turn on dark mode in the phone settings: all text still readable.
11. Turn the phone to airplane mode, tap Book: the browser's own offline page appears (nothing to check in ClassBook).
Screen reader (optional, if you have one): headings list shows one top heading per page and sensible names for buttons.
