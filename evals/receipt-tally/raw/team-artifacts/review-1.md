# Review 1 - T1 + T2 (Receipt Tally), pr-reviewer -> developer

Ran: `python -m unittest discover -s tests` (36 pass, 294 package lines, no float, stdlib only). Then probed the real program with hostile inputs (scratch files outside the repo). The happy path matches the spec; the problems are at the edges.

1. [MAJOR] Bad config values give a traceback, not a one-line error (spec section 4: bad config -> UserError, exit 2). Repro (config otherwise valid): `date_format = 5` -> `TypeError: strptime() argument 2 must be str` exit 1; top-level `rules = 5` -> `AttributeError: 'int' object has no attribute 'get'` exit 1. Also `amount = 5` is reported as "column '5' not found". Fix: in `load_config` check types (strings for column names/date_format, `rules` a table, `list` a list of strings); add tests. Consider a catch-all in `main` so no traceback ever shows.
2. [MAJOR] Money can be silently wrong (AC-4 / Correctness goal). `parse_amount` deletes every comma, so European `"1.234,56"` becomes 1.23456 (shown as 1.23); `"1_0.00"` is accepted as 10; `1e3` is accepted as 1000. A wrong total with no warning is worse than a skipped row. Fix: accept only an optional sign/symbol, digits with optional thousands commas in valid groups, and an optional 1-2 digit decimal part (regex), otherwise "bad amount"; test each case.
3. [MAJOR] If every row is bad (e.g. wrong `date_format`, the most likely beginner mistake), the run ends with only "no usable rows found in the bank file", exit 2, and the per-line problems (AC-10) are never shown. Repro: header + `x,A,1` row. Fix: include the problems (or at least the count and first few "line N: bad date 'x'") in that error; add a test.
4. [MINOR] Non-UTF-8 terminal/locale: with `PYTHONIOENCODING=ascii` and a description "CAFÉ" the program crashes with `UnicodeEncodeError` traceback in `cli.py` `sys.stdout.write`. Reconfigure stdout with `errors="replace"` or catch it as a UserError.
5. [MINOR] AC-17: control characters in descriptions are passed straight to the screen. A description containing `ESC[31m` printed a raw escape sequence, and an embedded newline broke the aligned column. Replace control characters (incl. newline) with a space in `render`; add a test.
6. [MINOR] `--month 2026-8` is accepted (strptime is lenient) and prints an empty "2026-8" summary. Require `^\d{4}-\d{2}$`.
7. [MINOR] `--out` with `--force` can overwrite the config file (only the bank file is protected). Cheap to refuse the same way.
8. [MINOR] Amounts with more than 2 decimals (`1.234`) are shown rounded without warning; tied to finding 2, decide: reject or show as-is.
9. [NIT] Handoff says `-k core` does not select tests; the spec's T1 verify command and `tests/fixtures/a.csv` path differ from what was built. Declared, acceptable; please update the spec's verify lines so they match.
10. [QUESTION] Skipped-row count and messages cover the whole file even when `--month` selects a month; declared and fine for Sam, just confirm the owner is happy with it.
11. [PRAISE] Clean module split, only `cli.py` does I/O, deterministic ordering, good AC-to-test mapping, socket and read-only tests, error messages that avoid descriptions (checked: only line numbers and bad date/amount text appear).

Verified OK: missing file, directory as bank file, binary file, NUL in text, empty/header-only file, `--out` into missing directory or onto an existing file without `--force`, determinism, no files created in dry-run.

VERDICT: CHANGES REQUESTED
