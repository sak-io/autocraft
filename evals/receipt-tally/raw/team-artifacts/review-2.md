# Review 2 - T1 + T2 (Receipt Tally), pr-reviewer -> developer

Ran `python -m unittest discover -s tests`: 45 pass. Package is 320 lines (limit 400), stdlib only. Re-probed the real program with hostile inputs (scratch files outside the repo).

## Round 1 findings, checked one by one
1. [FIXED] Bad config types: `date_format = 5`, `rules = 5`, `amount = 5` now give a one-line error, exit 2 (read in config.py, covered by test_review1).
2. [FIXED] Money parsing: `1,00.00`, `5.`, `.50`, `(5.00)` are skipped as bad amount; `1,234.50` and `£-5.00` parse right. European `1.234,56`, `1_0.00`, `1e3`, `NaN` are covered by tests.
3. [FIXED] All-bad-rows run now shows `(1 rows skipped; line 2: bad date '...')`, exit 2.
4. [FIXED] Non-UTF-8 stdout uses `errors="replace"`.
5. [PARTLY FIXED] Control characters are now cleaned in descriptions, but see new finding 12.
6. [FIXED] `--month 2026-8` and `2026-13` give a one-line error, exit 2.
7. [FIXED] `--out` onto the config file (also through a symlink) is refused even with `--force`.
8. [FIXED] More than 2 decimals is rejected, nothing is rounded silently.
9. [FIXED] Spec verify lines updated.
10. [ACCEPTED] Whole-file skipped count; README says so.

## New findings
11. [NIT] `parse_amount` uses `\d`, which also accepts non-ASCII digits (repro: Amount `١٢.٥٠` was read as 12.50). Harmless and still exact; `[0-9]` would be stricter.
12. [MINOR] AC-17 gap in the "problems" lines. The cell text echoed in `bad date '...'` / `bad amount '...'` is printed raw. Repro: a CSV row `ESC[1mbad,B,1.00` prints `line 5: bad date '^[[1mbad'` (cat -v) and a quoted amount containing a newline splits the line `line 4: bad amount '^[[31mred` / `x'`. Same class as round-1 finding 5, but on the other output path (also reaches the "no usable rows" error). Fix: pass the echoed text through the same control-character cleaning (and maybe cap its length), add a test. Not a blocker: needs a hostile or corrupt bank file.
13. [NIT] `.50` and `5.` are skipped as bad amounts. Safe (loud, never wrong), just noting it in case Sam's bank writes `.50`.
14. [PRAISE] Regression tests were written red first and the last-resort catch means no traceback ever shows.

No open BLOCKER or MAJOR. CI: no CI in this project; local tests are green on the latest commit. Finding 12 may be fixed now or tracked (note it in docs/STATUS.md).

VERDICT: APPROVED
