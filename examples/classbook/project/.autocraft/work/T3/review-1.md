# T3 review 1: accounts and sessions (pr-reviewer)

Branch `feat/T3-accounts` vs `main`. Reviewed code, tests and a live uvicorn. Full suite: 214 passed (1 pre-existing warning). CI is not available here (protocol s12); the suite is the gate.

## What it means for you
Sign-up, sign-in and sign-out work and held up when I attacked them. Nothing blocks the merge. The notes below are small hardening items; none of them need to be done before merging.

## Probed for real (uvicorn, fresh database each time)
- Sign-up 303, session cookie `HttpOnly; SameSite=Lax; Path=/; Max-Age=1209600`; `__Host-session` + `Secure` in production (test_auth_routes.py:196). Logout cookie cleared with same attributes, CSRF cookie rotated.
- Old cookie after logout: `/logout` replays as anonymous (303 /login). Forged/garbage/oversized (5000 char)/SQL-looking cookies: page renders anonymous, no error.
- Fixation: presented token `AAAA...` at login is not reused; a new cookie is issued (accounts.py:68-69).
- Wrong password vs unknown email: both 401, identical body; median latency 52 ms vs 50 ms.
- `next` = `//evil.com`, `/\evil.com`, `https://evil.com`, `/%2fevil.com` all land on `/`; `/ok` kept.
- Throttles: 10 failures on one email from 10 different IPs, 11th is 429 with `Retry-After: 900`. With `TRUSTED_PROXY_HOPS=1` and `--no-proxy-headers`, 22 attempts with spoofed left-hand `X-Forwarded-For` entries are keyed to the real hop and cut off at 20 (429). Sign-up with correct data after a locked email still works for other emails.
- Password / email never appear in the server log (grepped); only `login failed`, `login ok user_id`.
- Admin bootstrap, started for real: short password refuses (config); create; email change refused without flag, works with flag; env password change resets; email change onto a student's address refused even with flag; student promotion refused without flag, works with flag. Messages name settings, not values.
- scrypt N=2^14, r=8, p=1, 16-byte random salt, `hmac.compare_digest`, versioned prefix (passwords.py:9-32). Password capped at 128 (validator for sign-up, truncation at login accounts.py:61). Every `hash_password`/`verify_password` call is outside `write_tx` (accounts.py:61,100; bootstrap.py:31,47).
- Note for local runs: plain `uvicorn` (without `--no-proxy-headers`) rewrites the client address from `X-Forwarded-For` when the caller is loopback, which defeats the IP cap. The Dockerfile sets the flag (checked by a test), so production is fine.

## Checks against ADR-0003 and the authentication capability
All ADR-0003 conditions met (128 cap, hashing outside transactions, dummy verify, prefix-swappable hasher). Safe defaults met (httpOnly/sameSite cookies, logout truly ends the session, throttle, server-side checks). "Must test" met except where owned by other tasks (authz matrix and route guards are T7; reset links do not exist yet). Common mistakes: no email enumeration found in the responses.

## Findings
- [PRAISE] Throttled attempts are not recorded, so an attacker cannot extend a victim's lockout; unknown emails are counted under the same key so lockouts do not reveal accounts (service.py:36-38, accounts.py:56-64).
- [PRAISE] Tests assert behaviour (cookie replay after logout, CSRF old-token 403 after rotation, identical bodies, spoofed XFF, log content). Size is mostly tests and cohesive (one fixture set); splitting would not help.
- [MINOR] passwords.py:35 `dummy_hash()` is built lazily, so the first unknown-email login after each start does two scrypts (~100 ms) and is measurably slower than a wrong password: a one-time timing signal. Call `dummy_hash()` once in `create_app` (or at import). Same for any future test of timing.
- [MINOR] No test pins the ADR parameters or the "no hashing inside a write transaction" condition (both are ADR-0003 conditions). Add: assert `passwords.N, R, P == (2**14, 8, 1)` and the hash is `scrypt1$<32 hex>$<64 hex>`; and one test that patches `hash_password`/`verify_password` to assert `conn.in_transaction` is false (or that `write_tx` is not active) during login, sign-up and bootstrap. Also add a login test with a 129+ character password to show the truncation does not 500 (accounts.py:61).
- [MINOR] bootstrap.py:36-38 promotion keeps the student's bookings. An admin with active bookings will appear in rosters and cannot cancel them (admin cannot book/cancel by T5 rules). Either cancel/keep deliberately and say so in the handoff, or note it for the T8 runbook. Not a security issue.
- [NIT] Throttle check and failure record are in different transactions (accounts.py:55-64), so a burst of parallel requests can exceed the cap by about the thread-pool size once. Acceptable at this size; worth one line in the threat model residual (T-4).
- [NIT] accounts.py:44-46 and 77-78: signed-in visitors can open /login and /signup (handoff choice 6). Fine; consider a redirect later.
- [QUESTION] None open.

Handoff choices 1-7 are reasonable and accepted. The `test_web_shell.py` edit is sound.

## Not verified here
CI/secret scan/pip-audit (no pipeline in this environment); behaviour behind a real proxy (F23, T8 smoke checklist).

No open BLOCKER or MAJOR. MINORs may be fixed in T3 or tracked for T7/T8.

VERDICT: APPROVED
