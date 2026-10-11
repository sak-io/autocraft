# ClassBook test plan (T7, cross-task assurance)

Author: qa-engineer (did not write the code under test). Spec: `docs/specs/classbook.md` (AGREED, with change log).
Where each acceptance criterion (AC) is proven: `docs/qa/traceability.md`. Results and defects: `docs/qa/qa-summary.md`.

## 1. What this means for the owner
Every promise in the spec has at least one automated test that fails if the promise is broken. The tests drive the
real program (real sessions, real database file, a real `uvicorn` web server for the important ones), not stand-ins.
You do not need to run anything; `python -m pytest` runs all of it in about one minute.

## 2. Scope
In: everything built in T1 to T6 (schedule, sign-up and sign-in, booking and cancelling, admin class management,
confirmation emails, security headers, CSRF, throttles) and how the pieces work together.
Out (not built yet, belongs to T8): hosting, `render.yaml`, nightly backup, `/admin/backup`, restore rehearsal, uptime
monitor. The route that is documented but not built (`GET /admin/backup`) is listed explicitly in
`tests/qa/test_route_guards.py` (`NOT_BUILT_YET`), so the day T8 adds it the tests force it into the guard table and
the authorisation matrix.

## 3. Approach
1. **Derive tests from the acceptance criteria.** Each AC maps to named tests in the traceability matrix. An AC with no
   test is marked in that file; there are none.
2. **Cross-task tests** (what the per-task reviews could not see): the route-guard enumeration, the full authorisation
   matrix, the booking race over real HTTP, the end-to-end journey, accessibility of the served HTML, the follow-ups
   handed over by the reviews.
3. **Exploratory testing**: drive the running app like a hostile user and like a confused user. Everything found is
   kept as an automated test. A real defect is never fixed by QA: it becomes a strict `xfail` test named `DEFECT D-n`
   (fails today by design, and flips to "unexpectedly passed" the moment a developer fixes it) plus an entry in the QA
   summary.
4. **Mutation probes** (`tests/qa/mutation_probes.py`): apply 21 plausible wrong changes to a throw-away copy of the
   code (mail sent inline, student email in the body, hashing inside a write transaction, weaker scrypt, lock timeout
   answering 500, studio cancel sending mail, an empty router, a removed guard, no ownership check, missing label,
   removed `lang`, second `h1`, removed focus outline, pale text, `BEGIN` instead of `BEGIN IMMEDIATE`, weaker
   full-class check, removed duplicate-booking check, studio cancel not cancelling bookings, non-HttpOnly cookie). A test
   that cannot fail is not a test; all 21 are caught.

## 4. Test levels and where they live
| Level | Where | Notes |
|---|---|---|
| Unit | `tests/test_rules.py`, `test_timeutil.py`, `test_validators.py`, `test_auth_unit.py`, `test_web_util.py` (T1-T6) | boundaries: 12 h exact, day 30 and +1 s, DST gap and fold |
| Integration | `tests/test_*.py` (T1-T6) | real temp-file SQLite with production pragmas, FixedClock |
| **Cross-task in-process (T7)** | `tests/qa/` | real sessions, no dependency overrides; copies of one seeded database per test |
| **End-to-end over real HTTP (T7)** | `tests/e2e/` | `uvicorn` as a separate process, exactly like the Dockerfile `CMD` (one worker, `--no-proxy-headers`), httpx clients, the real database file and the process log inspected afterwards |
| Manual | checklist at the end of `docs/qa/qa-summary.md` | keyboard and phone pass; needs a person and a real phone |

New files: `tests/qa/test_route_guards.py`, `test_authz_matrix.py`, `test_followups.py`, `test_accessibility.py`,
`test_exploratory.py`, `support.py`, `conftest.py`, `mutation_probes.py`; `tests/e2e/conftest.py`,
`test_booking_race_http.py`, `test_journey_http.py`, `test_live_exploratory.py`.

## 5. Risk areas and edge cases
| Edge case | Why it matters | Where tested |
|---|---|---|
| **Concurrent** (50 people, 1 spot; 30 on 10; double click; cancel vs book; studio cancel vs book) | never overbook; one email only | `tests/e2e/test_booking_race_http.py` (real HTTP), T5 thread tests |
| **Unauthorised** (visitor, student, other student, admin on every route; CSRF on every POST; wrong HTTP methods; id guessing) | students must only touch their own data; only Maya manages classes | `test_route_guards.py`, `test_authz_matrix.py` |
| **Duplicate** (double submit, two tabs, repeated sign-up, rebook after cancel) | one booking, one email, one account | `test_exploratory.py`, `test_live_exploratory.py`, `test_journey_http.py` |
| **Time and time zones** (day 30 +/- 1 s, day 60, 12 h +/- 1 s, class starting this second, session 14 days, DST spring label, clocks moving between page load and click) | rules are exact to the second; London time shown | `test_exploratory.py` (HTTP), `test_rules.py`, `test_timeutil.py` |
| **Unicode / odd text** (emoji, right-to-left override, combining marks, SQL-looking text, markup) | escaping, cookie size, email text | `test_exploratory.py`, `test_mail.py`, `test_classes.py` |
| **Huge / malformed input** (23-digit ids, 200 KB URL and header, 20 KB body, lying `Content-Length`, bad UTF-8) | no crash, no 5xx | `test_exploratory.py`, `test_live_exploratory.py` |
| **Empty** (no classes, no bookings, empty roster) | friendly messages | `test_classes.py`, `test_accessibility.py` |
| **Lock timeout / busy database** on every write route | 503 page, nothing written, recovers | `test_followups.py` |
| **Restart** (no in-memory state needed) | host restarts the app | `test_live_exploratory.py` |
| **Slow network** | not simulated (see residual risk) | manual checklist |
| **Accessibility** | phones and keyboard are in the spec | `test_accessibility.py` + manual checklist |

## 6. Entry and exit criteria
Entry: T3-T6 merged on `main`, 344 tests green.
Exit for T7: every AC has a named test; zero unguarded routes; the race, journey, accessibility and follow-up tests pass;
no flaky test (three full runs identical); every defect found is written up with severity and a reproducing test;
residual risk stated. Open defects do not block T7; the owner decides which to fix before release.

## 7. How to run
```
python -m pytest -o addopts=''                 # everything (about 1 minute)
python -m pytest tests/qa                      # cross-task, in-process (seconds)
python -m pytest tests/e2e -s                  # real uvicorn tests; prints the measured p95 of 30 simultaneous bookings
python -m pytest -rx tests/qa/test_exploratory.py tests/qa/test_accessibility.py tests/qa/test_followups.py   # list the open defects
python tests/qa/mutation_probes.py             # 21 mutants, expect CAUGHT for each
```
Tests are deterministic: time comes from `FixedClock` (in-process) or is compared only relative to the real clock with
days of margin (real-HTTP tests); there are no sleeps, only a bounded wait for the background email to be recorded.

## 8. Defect handling
Severity: `[BLOCKER]` wrong, insecure or breaks the main flow; `[MAJOR]` significant gap; `[MINOR]` should fix, may be
deferred. Each defect `D-n` has a strict-`xfail` test whose `reason=` holds the description. When a developer fixes it
the test reports "XPASS(strict)" and fails the build until the `xfail` marker is removed, which turns the test into the
regression test.
