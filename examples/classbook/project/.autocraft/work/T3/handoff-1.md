# T3 handoff 1: accounts and sessions

Branch `feat/T3-accounts` (from main, contains T1+T2). No GitHub: this file is the pull request (protocol s12).
Size: about 390 changed lines of code and templates, about 530 of tests (over the 400 guide, mostly tests; not split because throttle, bootstrap and sessions share one set of fixtures).

## What and why
Imports the T1 kernel and T2 shell (`write_tx`, `Clock`, validators, `client_ip`, `safe_next`, `rotate_csrf`, `flash`, `render`, `cookie_name`); re-implements none of it.
- `classbook/auth/passwords.py`: stdlib scrypt (N=2^14, r=8, p=1, 16-byte salt), format `scrypt1$salt$hash`, `compare_digest`, `dummy_hash()` for unknown emails.
- `classbook/auth/service.py`: sessions (256-bit token, SHA-256 at rest, 14 days, expiry exclusive), throttle counters in `login_failures`, `purge_expired`, `mark_sign_in`, `last_sign_in()` (the "last sign-in" data for the T4 admin page: previous login time and failures on the admin email since).
- `classbook/auth/bootstrap.py`: admin cases (a) create / refuse student promotion without `ADMIN_PROMOTE_EXISTING`, (b) refuse email change without `ADMIN_ALLOW_EMAIL_CHANGE`, (c) env password that does not verify resets the stored one. Refusal raises `BootstrapError`; `create_app` prints the message (names settings, never values) and exits 1. Admin password < 14 was already refused by T1 config; now tested here.
- `classbook/auth/web.py`: session cookie (`__Host-session` in production, `session` otherwise, HttpOnly, SameSite=Lax, Secure iff production, Path=/, Max-Age 14 days) and `user_from_request`.
- `classbook/web/deps.py`: `current_user` seam now calls it (still overridable with `dependency_overrides`; test included).
- `classbook/routes/accounts.py`: `GET/POST /login`, `GET/POST /signup`, `POST /logout` (api.md #3-#5); templates `login.html`, `signup.html`.
- `app.py` (additive): bootstrap + purge at startup. `web/__init__.py`: 429 and 503 messages. `Dockerfile`: `--no-proxy-headers`. `.env.example`: documents the two flags (F25).

## How to verify
- `venv/bin/python -m pytest` (whole suite) and `venv/bin/python -m pytest tests/test_auth_unit.py tests/test_auth_routes.py -v`
- Manual: `ADMIN_EMAIL=maya@example.com ADMIN_PASSWORD=a-long-test-password-123 uvicorn --factory classbook.app:create_app`, open /signup, /login.
- Bootstrap refusals: start with an existing student on `ADMIN_EMAIL` (exit 1, message names `ADMIN_PROMOTE_EXISTING`).

## pytest summary
`214 passed, 1 warning in 16.56s` (162 existing + 52 new; the one warning is the httpx/starlette deprecation already on main).

## Required-tests map
scrypt/token hashing/malformed hash: test_auth_unit. Forged/garbage/expired/logged-out cookie: test_forged_garbage_and_expired_cookies_are_anonymous, test_logout_deletes_session_.... Throttle: per-email cap (10 IPs, then correct password still 429, window expiry), per-IP cap, spoofed XFF with hops=1 and hops=0, unknown emails counted, sign-up 10/hour/IP. Bootstrap: 3 cases plus promote-with-flag, email-change-with-flag, new-email-taken, sessions ended, messages free of secrets. Generic errors: wrong password vs unknown email render identically (401), duplicate sign-up is the generic 422; dummy-hash path asserted. Password never logged: test_login_failure_log_line_has_no_email_or_password. CSRF rotation at login and logout: cookie value changes, old token then gets 403. F22: /login and /signup are `no-store`.

## Choices where the docs were silent
1. Sessions: login deletes the session whose cookie the browser presented, other devices' sessions stay. Bootstrap promote / email change / password reset deletes that admin's sessions (a reset password should end old sign-ins).
2. Throttle: a throttled attempt is not recorded (no self-extending lockout); successful logins do not clear failures (so "failures since" is truthful). Unknown emails are throttled and counted under `email:` too, so lockouts do not reveal accounts. Sign-up counts every attempt (incl. 422s); the 11th in an hour gets 429. Keys live in `login_failures` (`email:`, `ip:`, `signup:`), purged after 1 day at startup and once per 24 h on a login.
3. Login body fields over 128 chars are truncated before hashing; email truncated to 254. Invalid email shapes at login are just a failed login (401), not 422.
4. Status codes: 401 failed login, 422 sign-up validation, 429 with `Retry-After` through the shared error page.
5. Promote keeps the student's name; new admin is named "Studio admin".
6. Already-signed-in visitors may still open /login and /signup (no redirect).
7. Sign-in also sets `last_login_at` on sign-up.

## Deviations / for the reviewer
- Merge-conflict heads-up: I edited `tests/test_web_shell.py::test_empty_routers_are_registered_by_the_factory` (renamed, dropped the "routers are empty" assert, which cannot hold once any router has routes). T4/T5 will need the same edit; accept either side.
- `app.py` now runs bootstrap before building the app (needs `Clock` earlier; `app.state.clock` unchanged). No architecture deviation otherwise; no new dependencies.
- Redaction is by key name only: auth code logs only `user_id`, `actions` (a list of fixed words) and fixed messages.

## Not done / belongs elsewhere
- Admin page showing "last sign-in" (T4 calls `auth.service.last_sign_in(conn, user_id)`); route-guard enumeration and authz matrix (T7); nightly purge beyond startup + login trigger (acceptable at this size; T8 may add a timer).
- Nav links to /my-bookings and /admin/classes still point to routes T4/T5 add.

HANDOFF
To: pr-reviewer
Task: T3 accounts and sessions, branch feat/T3-accounts, files in `.autocraft/work/T3/handoff-1.md`
Focus: auth/passwords.py, auth/bootstrap.py (three cases and refusals), routes/accounts.py (throttle order, generic errors, no user data in logs, csrf rotation), cookie flags, tests for spoofed XFF and per-email cap.
Open items: none blocking; choices listed above.
