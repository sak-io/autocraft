# T5fix handoff 1: test fixture vs admin bootstrap

Branch `fix/T5-fixture-vs-bootstrap` (from main with T1-T3, T5). Test-only; no production code changed.

## Cause
T3's startup bootstrap creates the single allowed admin inside `create_app`. T5's `http` fixture created the app first and then inserted its own admin row, hitting the one-admin unique index (`UNIQUE constraint failed: users.role`): 12 errors in `tests/test_bookings.py`.

## Fix
`http` fixture now migrates the DB and inserts the two students and the class BEFORE `create_app`; the bootstrap then creates the admin as id 3, keeping ids 1=A, 2=B, 3=admin used by the tests. The fixture asserts that id. The one-admin index is untouched.
`tests/test_web_shell.py`: replaced the removed routers assertion with "accounts and bookings routers have routes". Deviation from the request: `classes` router is still empty on main (T4 not merged), so "every router" fails today; extend the assert when T4 merges.

## Verify
`$PY -m pytest` -> `249 passed` (whole suite).

HANDOFF
From: developer            To: pr-reviewer
Status: DONE
Summary: Fixed T5 http fixture to create students before app startup so the T3 admin bootstrap does not collide; routers assertion restored for accounts and bookings. 249 passed.
Artifacts: branch fix/T5-fixture-vs-bootstrap; .autocraft/work/T5fix/handoff-1.md
Open items: classes router assertion waits for T4.
Next: review; human merges.
