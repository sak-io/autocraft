# T7 handoff 1: cross-task assurance (qa-engineer)

Branch `test/T7-cross-task-assurance` (worktree `wt-T7`, from `main` = T1-T6, 344 tests). Test-only and docs; **no production code changed**.

## What this means for the owner
The app holds up: no blockers, no major defects. Nine small defects (all MINOR) are written up in `docs/qa/qa-summary.md`
as D-1 to D-9, each with a test that fails on purpose today. Nothing for you to do now; the QA summary has a 15-minute
keyboard and phone checklist for you to run once before students use it.

## What I did
1. `docs/qa/test-plan.md`, `docs/qa/traceability.md` (every AC, change-log item, answered question and NFR to named tests; none without a test), `docs/qa/qa-summary.md`.
2. `tests/qa/` (in-process, real sessions): `test_route_guards.py` (enumeration, declared guard table, self-test, router-has-routes, api.md parity), `test_authz_matrix.py` (72 cells, CSRF on all 8 POST routes, 405s, id probing), `test_followups.py`, `test_accessibility.py`, `test_exploratory.py`, `support.py`, `conftest.py`, `mutation_probes.py`.
3. `tests/e2e/` (real `uvicorn` process): `test_booking_race_http.py`, `test_journey_http.py`, `test_live_exploratory.py`, `conftest.py`.
4. 21 mutation probes on a copy of the code: 21 caught (`python tests/qa/mutation_probes.py`).

## Commands
```
python -m pytest -o addopts=''                         # all
python -m pytest -o addopts='' -rx tests/qa tests/e2e  # also lists the 9 open defects (strict xfail)
python tests/qa/mutation_probes.py                     # mutants, expect CAUGHT x21
```
## Result
`521 passed, 14 xfailed, 1 warning in ~65s` (three identical full runs; before T7: `344 passed`). The 14 xfails are the 9 defects (D-1 x3 paths, D-2 x4 paths, D-3..D-9 x1).

## Defects (all MINOR; details and reproduction in docs/qa/qa-summary.md)
- D-1 POST book/cancel with a 64-bit-overflow id -> 500 (should be 404).
- D-2 non-numeric id in the URL -> raw JSON 422 (should be the 404 page).
- D-3 `HEAD /health` -> 405 (uptime monitors may use HEAD).
- D-4 `dummy_hash()` lazily built: first unknown-email login is slower (95 ms vs 52 ms). Carried from T3 review.
- D-5 bare error pages (503, form expired, 413, 500) lack the viewport meta and stylesheet.
- D-6 no `overflow-wrap`: long unbroken names/titles scroll sideways on phones (confirm on a phone).
- D-7 admin page lacks the "failed sign-ins since" count (`last_sign_in()` unused); AR-1 mitigation incomplete.
- D-8 greyed classes do not show "spots left" although AC-1.1 reads that way (fix the page or amend the spec).
- D-9 signed-in user sees the signed-out menu on 404/405 pages.

## HANDOFF
```
HANDOFF
From: qa-engineer            To: pr-reviewer (then human)
Status: DONE
Summary: Cross-task assurance finished with test and doc changes only. 521 passed, 14 xfailed (9 open MINOR defects reproduced as strict xfail tests); no BLOCKER or MAJOR. Route guards enumerated and complete; 72-cell authz matrix, real-HTTP race (50 on 1 spot -> exactly 1; p95 0.36 s), real-HTTP journey with emails, accessibility and follow-up tests all pass; 21/21 mutation probes caught.
Artifacts: docs/qa/test-plan.md, docs/qa/traceability.md, docs/qa/qa-summary.md, tests/qa/*, tests/e2e/*, .autocraft/work/T7/handoff-1.md (branch test/T7-cross-task-assurance)
Open items:
 1. A developer to fix D-1..D-9 (suggest D-1, D-3, D-5, D-7 before opening to students); then remove each `xfail` marker (the test becomes the regression test).
 2. Owner: run the keyboard/phone checklist (qa-summary.md); decide D-8 (add spots-left to greyed rows or amend AC-1.1) and confirm the "30 days = 720 hours" reading (O-2); consider raising the sign-up cap (O-3).
 3. Orchestrator: record in docs/STATUS.md; api.md row 6 note about the cap-first order (T5 M-1) is still not written; T8 runbook items in qa-summary O-7.
 4. T8: when `GET /admin/backup` lands, remove it from NOT_BUILT_YET in tests/qa/test_route_guards.py and add it to POLICY and the matrix (the parity test forces this).
Next: pr-reviewer reviews the test code (read tests/qa and tests/e2e; run the commands above); human merges.
```
