# H1 brief: fix QA + security findings (token_mode: lean; budget ~120k tokens, <=70 tool calls)
Work ONLY in this worktree (branch fix/H1-qa-and-security). Read this brief, then only the files you must edit. Do not re-read specs/ADRs. Venv: VENV/bin/python -m pytest -o addopts='' -q (path given by lead).
Defects are strict-xfail tests already written (tests/qa/*). For each: fix code, remove the xfail marker so it becomes a regression test, keep it green.
- D-1 huge ids (POST /classes/{id}/book, /bookings/{id}/cancel) -> 404 not 500 (SQLite int overflow; bound-check ids in one shared path helper).
- D-2 non-numeric ids in URLs -> HTML 404 page (not JSON 422).
- D-3 HEAD /health -> 200.
- D-4 warm dummy_hash() at startup (lifespan), not on first sign-in.
- D-5 bare error pages (503/403/413/500) get viewport meta + stylesheet link.
- D-6 css overflow-wrap so long names do not overflow on phones.
- D-7 admin page shows failed-attempt count (see test_exploratory D-7 for what is expected).
- D-8 OWNER DECISION: greyed (full/past) rows show NO spots-left number. Change the xfail test to assert that (spec already amended) and make the code match if it does not.
- D-9 404/405 pages: no signed-in menu leakage inconsistency (see test).
Security (docs/security/audit-2026-10-10.md): M-2 throttled sign-up attempts must not each write a row (cap/skip recording once throttled, so disk cannot be filled); L-3 purge old user_actions and messages in the existing retention job; L-5 CSP add form-action 'self', base-uri 'none', frame-ancestors 'none', HSTS includeSubDomains; L-7 os.umask(0o077) before creating the DB file.
Add a unit/regression test for M-2, L-3, L-5, L-7 (one each, small). Do NOT touch M-1, M-3, L-2, L-4, L-6 (deferred to T8).
Process NFR (add to docs/spec/ NFR table where NFRs live, one row): "Token efficiency: the team builds and maintains ClassBook within a stated token budget (token_mode: lean)". 
Done = full suite green (0 failed, 0 xfail left except none), `bandit -q -r classbook` no new findings. Commit in small logical commits. Write .autocraft/work/H1/handoff.md (<=25 lines): commits, what changed per ID, test counts, anything not done. Reply with <=10 lines.
