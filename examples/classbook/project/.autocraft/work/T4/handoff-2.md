# T4 handoff 2 (answers to review-1)

Branch merged with main twice (T3 + T5 + the T5 fixture fix); no conflicts remained. Full suite, no deselects: see below.

- M-1 Fixed in 635ad57 (test_roster_lists_only_booked_students: booked + student-cancelled + after class cancel). Verified by mutation: removing `AND b.status = 'booked'` from the roster query fails that test; restored.
- m-1 Fixed in 2523e19 (get_class maps OverflowError to 404) and 635ad57 (public page, admin detail/edit, update and cancel with a 23-digit id all 404).
- m-2 Fixed in 2523e19: owner decision applied. Cancelling a started class returns 409 "already started", changes nothing; button hidden for started classes (and cancelled). Pinned in 635ad57 (test_cancelling_a_started_class_is_refused_and_button_hidden). A cancelled class is still a 303 no-op.
- m-3 Fixed in 2523e19: opacity removed; greyed rows use dashed border plus --muted colour. Test in 635ad57 computes WCAG contrast from style.css: --muted on white and on dark --bg both >= 4.5:1 (about 5.9:1 and 7.6:1 by hand) and asserts no opacity on .greyed.
- m-4 Fixed in 635ad57 (test_second_cancel_says_already_cancelled follows the flash on the detail page).
- n-1 Fixed in 2523e19: capacity-below-bookings now reported beside other field errors (422 when other errors exist, 409 when it is the only one); test in 635ad57.
- n-2 Not changing: trivial, one cheap call per row.
- n-3 Not changing: STATUS.md is the orchestrator's.
- After merging T3: the admin row now exists at app start (bootstrap), so my seed fixture only updates it instead of inserting (9ee4e54).

HANDOFF
From: developer            To: pr-reviewer
Status: DONE
Summary: All review-1 findings addressed (M-1 roster test with mutation check, huge-id 404, started-class cancel refused, AA contrast, flash test, capacity error visibility); merged with main.
Artifacts: branch feat/T4-schedule-admin; .autocraft/work/T4/handoff-2.md
Open items: none
Next: re-review per protocol s12 into review-2.md.
