# H1 review (independent) - branch fix/H1-qa-and-security
Suite re-run: 539 passed, 0 xfail. Probes were throwaway scripts (deleted). No code changed.

## Probed
- (a) M-2 OK. 14 sign-ups: 10x 303 then 429 from the 11th; exactly 10 signup rows, none after throttle. X-Forwarded-For, X-Real-IP, Forwarded headers do not bypass (still 429); empty form while throttled -> 429. Check+record share one write_tx. Mutation (restore record-before-check) makes test_m2 fail, so the test is not vacuous.
- (b) ids 007, 1/2/3 fullwidth digits, Arabic-Indic '١٢٣', -1, 0, +1, 1.0, 1e3, 10**30, 2**63, 2**63-1, whitespace, %00, %ff, 5000 chars, trailing newline, across 7 routes x admin/student/anon: no 500, no JSON 422, no exceptions; unknown -> HTML 404. Only 422 seen: POST /admin/classes/1 with an empty form (legit HTML validation).
- (c) D-7 OK: admin sees "2 failed sign-in attempts ... since then", counting only the admin's own email key and only after prev_login_at (older and other users' failures excluded). Not present for student/anon on /, class page, /bookings, /admin/classes, 404.
- (d) CSP exact value, XFO, nosniff, referrer on 200, 404, 403 (csrf), 413, static, HEAD /health, missing static. DB file mode 0600 under a 022 umask (L-7). 403 page has viewport.

## Lighter checks
- D-3/4/5/6/8/9, L-3 read in diff: fine. L-3 purge: user_actions >1 day (booking cap uses 1 hour only), messages >90 days; both by timestamp only, no active data (sessions, bookings, classes) touched.
- Formerly-xfail tests: all 9 xfail markers removed; assertions otherwise unchanged. The only assertion edits are D-8 (owner decision, now asserts "Opens for booking on" and no "N spots left") and the two CSP strings.

## Findings
[MINOR] tests/test_web_shell.py now compares headers to the imported CSP constant, so those two assertions are tautological. The literal policy is pinned only by test_l5, which does substring checks. Suggest one literal full-string assertion.
[MINOR] os.umask(0o077) in create_app is process-global (also affects log files, tmp files, later created dirs, and the test process). Acceptable for a single-app process but worth a code comment; the parent-dir mkdir happens after it so the data dir becomes 0700 (fine).
[MINOR] Admin banner appears only if prev_login_at exists; failures before the first-ever sign-in are not surfaced. Edge, matches prior behavior.
[MINOR] messages purge at 90 days drops the (booking_id, kind) idempotency record; harmless unless a mail is re-sent for a >90-day-old booking. Confirm retention choice with owner (handoff already flags it).
[NIT] style.css has two separate body rules; handoff says "9 xfail" vs "6" in the brief. L-7 test does not cover WAL/SHM files (none present at rest).

No BLOCKER or MAJOR.
Verdict: APPROVE
