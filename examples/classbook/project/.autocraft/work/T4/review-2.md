# T4 review, round 2

Reviewer: pr-reviewer. Branch head `c98dc48`. Verified individually against the code, not the handoff.
Suite (run by me, `-o addopts=''`): **307 passed** (merged T3 + T5 + fixture fix). No conflict markers, no unmerged index entries. T4-owned diff since round 1 is limited to `classes.py`, `style.css`, `admin_detail.html`, `tests/test_classes.py`.

## Status of previous findings
| ID | Status | Evidence |
|---|---|---|
| M-1 roster booked-only untested | RESOLVED | `test_roster_lists_only_booked_students` (booked + cancelled + after class cancel). I re-ran my mutation (drop `AND b.status = 'booked'`, `classes.py` roster query): tests fail (caught). |
| m-1 huge id 500 | RESOLVED | `get_class` maps `OverflowError` to 404 (`classes.py:44-48`); test hits public page, admin detail, edit, update, cancel with a 23-digit id. Mutating the except clause is caught. |
| m-2 cancel of started class | RESOLVED (refuse, owner decision) | `admin_cancel` uses `state_of`; started -> 409 "already started", no change to class or bookings; button hidden unless state not in (cancelled, started) (`admin_detail.html:12`). Test also asserts a future class still shows the button, and cancelling a future class still works (`test_cancel_marks_class...`, `test_second_cancel_says_already_cancelled`). Mutants `done = True` and `state != "cancelled"` are caught. Already-cancelled stays a 303 no-op. |
| m-3 contrast | RESOLVED | opacity removed; `.class.greyed` and its link use `--muted`. My computation: #5b6770 on #fff about 5.9:1; #a2adb5 on #14181b about 7.6:1 (both >= 4.5). Test computes this from `style.css` and rejects `opacity`. |
| m-4 already-cancelled flash | RESOLVED | `test_second_cancel_says_already_cancelled` follows the flash text on the detail page. |
| n-1 capacity error hidden | RESOLVED | reported beside other errors (422 when others exist, 409 when alone); `status = 422 if errors else 409` mutant caught. |
| n-2 `view()` computes `opens` always | Accepted | trivial. |
| n-3 STATUS.md not updated | Accepted | belongs to the orchestrator. |

## New issues from the fixes
None found. Capacity check and UPDATE are still in the same `write_tx` as the `booked` read; the cancel path still performs both updates in one transaction; the shared `refuse()` page is used for the 409 and is autoescaped (static text). The seed-fixture change (UPDATE instead of INSERT for the bootstrap admin) is test-only and sound. The wider merge is other tasks' code and is outside this review's scope beyond the suite passing.

No open BLOCKER/MAJOR/MINOR.

VERDICT: APPROVED
