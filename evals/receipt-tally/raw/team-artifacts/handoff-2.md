# Handoff 2 - T1 + T2 review round 1 fixes (developer -> pr-reviewer)

New regression tests are in `tests/test_review1.py`. They were run before the fixes: 16 failures and 3 errors out of 45 tests (red). After the fixes: 45 pass, 0 fail (green). Package is 320 lines, stdlib only.

Fixes by finding:
1. [MAJOR] `load_config` now checks types: `date_format`, `amount`, `debit` and `credit` must be non-empty strings, `[rules]` must be a table and `list` a list of strings. All give a one-line `error:` and exit 2. `main` also has a last-resort catch so no traceback ever shows (one line, exit 1).
2. [MAJOR] `parse_amount` uses a strict regex: optional sign or symbol, digits with commas only as valid thousands groups, up to 2 decimals. `1.234,56`, `1_0.00`, `1e3`, `1,23`, `NaN` are now "bad amount" and the row is skipped.
3. [MAJOR] "no usable rows" error now reads `... (N rows skipped; line 2: bad date 'x'; ...)`, with the first 3 problems.
4. [MINOR] stdout is reconfigured with `errors="replace"`; subprocess test with `PYTHONIOENCODING=ascii`.
5. [MINOR] Control characters (including newline and ESC) in descriptions are replaced by a space in `render`.
6. [MINOR] `--month` must match `YYYY-MM` exactly (`2026-8` is rejected).
7. [MINOR] `--out` now refuses the config file as well as the bank file, even with `--force`.
8. [MINOR] Decided: reject more than 2 decimals (covered by finding 2), so nothing is rounded silently.
9. [NIT] Spec verify lines updated (no `-k core`, `examples/` paths).
10. [QUESTION] Owner decision: whole-file skipped count is fine. README now says so.

Disagreements: none.
Note: tests import `test_cli` helpers, so run via `python -m unittest discover -s tests` or `python -m pytest tests`.
