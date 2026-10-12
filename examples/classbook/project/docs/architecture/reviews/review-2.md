# Architecture review – round 2
Verdict: APPROVED

## Summary
In plain words: the architect fixed everything I raised in round 1, and I checked each fix in the documents themselves (not just in the "Review responses" text). No BLOCKER or MAJOR findings remain, so the design can go to build. A few small items (F22-F27 below) are tracked for the developers; none needs a decision from Maya. One thing must happen before the booking and schedule tasks start: the requirements-analyst must update the spec to match the agreed changes (greyed far-future classes, "cancelled by the studio", admin password length), because the spec is the source of truth.
Re-checked against the documents: CSRF before a session, the one-admin rule in the database, the throttle behind a proxy, shared rules in T1/T2, and an early deploy step.

## Status of previous findings
| # | Sev | Status | Check against the new documents |
|---|---|---|---|
| F1 | MAJOR | Resolved | `api.md` #2 adds `GET /classes/{id}`; visitor sees "Sign in to book" -> `/login?next=/classes/{id}`; after login/signup lands on a GET page. Journey test (visitor -> login -> class -> book) in T7. |
| F2 | MAJOR | Resolved | `architecture.md` s5: double-submit `__Host-csrf` cookie set on first GET of any form page, so `/login` and `/signup` work without a session; `csrf_token` column removed from `sessions`; rotated at login/logout; `csrf_field()` in T2 with a template scan test. Small follow-up in F22. |
| F3 | MAJOR | Resolved | s3: partial unique index on `role` WHERE `role='admin'` (at most one admin, enforced by the database; T1 tests "second admin rejected"). s5 bootstrap cases a-c with refusal flags; T3 tests the cases. Ambiguity in F25. |
| F4 | MAJOR | Resolved (with a verification step, F23) | s5: `TRUSTED_PROXY_HOPS` takes the right-most trusted XFF entry; per-email cap (10/15 min, any IP) plus per-IP cap (20/15 min); counters in SQLite `login_failures` (survive restarts); sign-up keyed on IP; spoof test in T3; residual delay-of-admin-login accepted in T-4. |
| F5 | MAJOR | Resolved | `kernel/` (`is_bookable`, `opens_at`, `cancel_allowed`, `spots_left`, time parsing, `write_tx`, validators) is built in T1; `web/` helpers (csrf, flash, headers, IP helper, auth seams, `Mailer` protocol) in T2; T3/T4/T5 depend only on T2, touch different files and "import, never re-implement". `write_tx` uses autocommit plus `BEGIN IMMEDIATE`, with a contention test. Route-guard enumeration and full authz matrix are owned by T7. T4's listing test is tied to `is_bookable`. Residual wiring detail in F26. |
| F6 | MAJOR | Resolved | T1 now has Dockerfile, CI, JSON logging with request id, `/health`; host chosen (ADR-0005, Render, ceiling 10 GBP); T8 step 1 (deploy `/health` with a disk) can start right after T1 and runs in parallel with T2-T5; E2E/a11y moved to T7, ops/backups/runbook to T8. Blocked-on-human steps are listed for Maya. |
| F7 | MINOR | Resolved | ADR-0003 rewritten on the real reasons; scrypt N=2^14,r=8,p=1; 128-char cap; hashing outside write transactions; dummy verify; versioned prefix; AR-1 named. |
| F8 | MINOR | Resolved | Fixed rule order in `api.md` #6/#8 and s4; `now` read once after the lock (s3). |
| F9 | MINOR | Resolved | 30x24h definition, gap rejected, fold = first occurrence, edit into the past rejected (s3; T1/T4 tests). |
| F10 | MINOR | Resolved | pending -> recorded/failed flow (ADR-0004, s6); retry caveat recorded; 20 actions/hour/user; control characters rejected; delivery gate until verification (ADR-0004, T-17, config refuses non-`recording`). Storage for the per-user cap is not named (F24). |
| F11 | MINOR | Resolved | Single `Secure` switch, `__Host-` prefixes, session purge, strict `next` validation (backslash, `%2f`, `%5c`, control chars). |
| F12 | MINOR | Resolved | Limits table, email shape check, 16 KB body cap in s3; validators in T1. |
| F13 | MINOR | Resolved (shape changed, accepted) | No external credentials: in-app nightly `VACUUM INTO` (7 kept), host snapshots, admin download; deletion semantics defined; continuous replication deferred with a reason. Note the same-disk copy does not protect against disk loss alone; the host snapshots and the monthly download do, and the residual data-loss window is documented. |
| F14 | MINOR | Resolved | External uptime monitor emails Maya; runbook line; unhandled-exception log test in T1. |
| F15 | MINOR | Resolved | AR-1 named in the threat model and accepted by Maya; admin password >= 14; "last sign-in" note. |
| F16 | MINOR | Resolved (as tracked) | Task split to 8 tasks; the architect keeps T1/T3 as one task each and lets developers split the PR if over 400 lines. Accepted. Real-HTTP race test in T7; tests use production pragmas. |
| F17 | NIT | Resolved | HSTS and Referrer-Policy added; WAL needs a local disk noted. |
| F18 | NIT | Resolved | `bookings.cancelled_by`; My bookings shows "cancelled by the studio"; still no email. |
| F19 | QUESTION | Resolved | Maya answered: Render, ceiling 10 GBP/month, step list in ADR-0005; price re-verified at sign-up (T8 stops and asks if over). |
| F20 | QUESTION | Resolved | Maya accepted admin without MFA/reset; recorded as AR-1 with the recovery procedure. |
| F21 | QUESTION | Resolved | Far-future classes are listed greyed with "Opens for booking on <date>" (api.md #1/#2/#6, s11); the spec update needed is itemised in s11 (see F27). |

## Findings (new, from the revision)
- [MINOR] F22 – Pages that contain a CSRF token must never be cached. `api.md` sets `no-store` only on authenticated pages, but `/login`, `/signup` and a visitor's `/classes/{id}` also embed the per-visitor token (the cookie is HttpOnly and the form value is copied from it). If a host proxy or browser caches such a page, the next visitor's form would carry a stale token and fail with 403. Fix: send `Cache-Control: no-store` on every response that renders `csrf_field()`; add it to the T2 test.
- [MINOR] F23 – The trusted-proxy rule rests on an unverified claim about the host (`architecture.md` s5: "Render adds the client IP as the right-most X-Forwarded-For entry"). If the host sits behind another proxy layer, `TRUSTED_PROXY_HOPS=1` could return a shared proxy address for everybody, and the per-IP caps (20 failed logins, 10 sign-ups per 15 min / hour) would then lock out all users at once. Fix: add to T8's deploy smoke checklist a step that logs the forwarded header once after the first deploy and confirms the hop count (and set `TRUSTED_PROXY_HOPS` accordingly); keep the per-email cap as the main login protection. Mark the claim as an ASSUMPTION in R4.
- [MINOR] F24 – Storage for the per-user "20 book/cancel actions per hour" cap is not defined; the only throttle table is `login_failures`. Say whether T5 reuses it (rename to a generic `throttle_events`) or logs from `bookings`/`messages`; clarify whether refused and no-op attempts count (suggest: only real bookings and cancellations count, refusals do not, so a stuck user is not locked out). Put the table in the T1 `0001` migration so T5 does not need to change the schema.
- [MINOR] F25 – The bootstrap flags are named but their effect is not: what does `ADMIN_ALLOW_EMAIL_CHANGE=true` do (move the admin to the new email, keeping the same account), and does `ADMIN_PROMOTE_EXISTING=true` also reset that student's password? Write one line each in s5 and make sure the T3 tests cover both flagged paths, not only the three refusals. Also state that flags should be removed after one boot.
- [MINOR] F26 – Wiring detail for the parallel tasks: the round 1 text said T1 registers empty routers so T3/T4/T5 touch different files; the round 2 T1/T2 rows do not say so. Add "T2 registers empty routers and template folders for accounts, schedule/admin and bookings" to avoid three PRs editing the app factory. Also `T8 step 1` plus T3/T4/T5 is four concurrent workers against a cap of three; T8 step 1 is mostly Maya's account work, so treat as fine but say so, or sequence it.
- [MINOR] F27 – Spec is out of date relative to the agreed design. `docs/specs/classbook.md` is marked AGREED, but AC-1.1, 1.2, 3.6, 3.7, 4.1, 6.3, the NFR table (admin password) and a new AC-1.5/Q8 change (listed in `architecture.md` s11). The developer's Definition of Ready (protocol s7) requires matching acceptance criteria. Gate: the requirements-analyst updates the spec (Maya confirms) before T4 and T5 start; T1-T3 can proceed.
- [NIT] F28 – `/admin/backup` includes the `sessions` table (hashes only) and login failures; excluding them from the downloaded copy reduces what a lost file reveals. Add a cap or a `no-store` rate limit on the endpoint (the 14-day session lifetime and the `VACUUM INTO` temp file are already covered).
- [NIT] F29 – "last sign-in ... count of failures since" reads from `login_failures`, which is purged daily; either keep the counter on the user row or say the count covers only the last day.

## Re-verification of the five points requested
- **T2..T5 independence:** yes. All shared rules are in T1/T2; T3 (auth), T4 (schedule/admin classes) and T5 (booking) use dependency overrides and fixture rows, and the only cross-links (login `next`, Book button on the class page, `is_bookable`) go through shared code. Combined behaviour is verified by T7, which now exists and names the guard test, the authz matrix, and the real-HTTP race. Remaining wiring risk is only F26.
- **CSRF before session:** specified and testable (cookie set on first form GET, double-submit comparison with `compare_digest`, rotation at login/logout, template scan). See F22.
- **Single admin enforced by schema:** yes, via a unique partial index, with startup refusals for the risky cases.
- **Throttle behind a proxy:** sound in design (trusted hop, per-email and per-IP, persisted); needs one live confirmation of the hop count (F23).
- **Skeleton deploys early:** yes: Dockerfile, CI, health in T1, deploy of `/health` with a disk as T8 step 1 right after T1; depends on Maya's sign-up steps, which are listed.

## Traceability and boundary check
All ACs still map to routes and tasks. Boundaries are consistent across code and listing: bookable iff `now < starts_at <= now+30x24h`; `opens_at = starts_at - 30x24h`; cancel allowed iff `starts_at - now >= 12h`; same `is_bookable` used by the schedule (T4) and booking (T5). Concurrency (AC-3.3, 6.2, 4.5) is covered by `write_tx`, derived spots-left and the partial unique index, with threaded and real-HTTP tests on production pragmas.

## What is good
- The shared kernel in T1 is the right fix: one definition of "bookable", "cancel allowed" and "spots left", so the page and the booking can never disagree, and parallel work is genuinely independent.
- The CSRF design, the bootstrap rules and the one-admin index close real attack paths in a small, testable way.
- The throttle design names its own weakness (admin login can be delayed 15 minutes) and accepts it deliberately instead of hiding it.
- The host choice is concrete, costed against Maya's ceiling, has a step list she can follow, and says to stop and ask if the price differs.
- The review responses are honest: one finding (F13) was handled differently with reasons, and the deferred continuous replication is recorded.

HANDOFF
From: principal-engineer            To: human (Maya / owner), then architect and requirements-analyst for follow-ups
Status: DONE
Summary: Round 2 verdict APPROVED. F1-F21 all resolved; 0 BLOCKER, 0 MAJOR open. 6 new MINOR (F22-F27) and 2 NIT (F28-F29) are tracked for the developers; none needs a human decision. `docs/architecture/status.md` set to APPROVED.
Artifacts: docs/architecture/reviews/review-2.md, docs/architecture/status.md
Open items: 1. Requirements-analyst updates the spec per architecture s11 (F27) and Maya confirms, before T4/T5 start. 2. Architect folds F22-F26 into the docs or the task acceptance criteria (small edits, can be done as notes in T1/T2/T3/T5/T8). 3. Maya completes ADR-0005 host sign-up steps (needed for T8 step 1, not for T1-T7). 4. Human approves the architecture (autonomy level 2) before development starts; humans merge all PRs.
Next: owner approves; then start T1 (single developer), followed by T2, then T3/T4/T5 in parallel.
