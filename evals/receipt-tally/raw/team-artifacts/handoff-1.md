# Handoff 1 - T1 + T2 (Receipt Tally), developer -> pr-reviewer
Spec: docs/specs/receipt-tally.md. Branch: session branch (git_mode session-branch), no PR.

## What this means for the owner
Sam can run `python -m receipt_tally bank.csv --config rules.toml` and get a monthly text summary. Nothing needed from Sam yet; waiting for independent review.

## What changed
- Commit 1 (T1): `receipt_tally/{__init__,config,parse,rules,summary}.py`, `examples/` (two fake CSVs, two sample configs), `tests/test_core.py`, `.gitignore`.
- Commit 2 (T2): `receipt_tally/{cli,__main__}.py`, `tests/test_cli.py`, `README.md`, this handoff.
- Package is 294 lines (limit 400), stdlib only. Money is `Decimal` only.

## How to verify
- `python -m pytest -q tests` (or `python -m unittest discover -s tests`)
- `python -m receipt_tally examples/bank_a.csv --config examples/config_a.toml`
- same with `bank_b.csv` / `config_b.toml`; add `--month 2026-08`, `--out r.txt [--force]`
- `cat receipt_tally/*.py | wc -l`

## Test evidence
36 tests, all pass (19 core, 17 CLI). Mapping to acceptance criteria:
AC-1/2/3 layout + mapping tests; AC-4 `test_money_is_exact`, `test_no_float_used_for_money`; AC-5/6/7 rule tests; AC-8 month summary tests; AC-9 missing-file (in-process and subprocess); AC-10 bad-row tests (core + CLI exit 0); AC-11 no files created; AC-12 `--out`/`--force`; AC-13 determinism (also input order reversed); AC-14 socket patched + import check in a subprocess; AC-15 bytes and mtime; AC-16 error text without descriptions, no extra files; AC-17 no ANSI, ASCII, aligned columns.

## Deviations / decisions to check
- Spec verify command uses `tests/fixtures/a.csv`; I used `examples/` as the fixtures instead (single copy). The unittest command in the spec also works via `discover`; test names do not contain "core" for `-k core` filtering of file `test_core.py` (use `-p test_core.py`).
- Default answers applied: no currency symbol; refunds net into categories; TOML config.
- "Total spending" is shown as a positive number; category totals are net and signed. Categories sorted by total ascending (biggest spend first), ties by name.
- Debit/credit cells: sign is taken from the column (abs value), so a negative Debit is still spending. Both empty -> "missing field 'debit/credit'".
- Skipped-row count covers the whole file, not only the chosen month. Bad-row notes are part of the rendered text, so they are also in an `--out` file.
- `--out` pointing at the bank file is refused even with `--force` (extra safety for AC-15).
- Success with `--out` prints one line "Summary written to <path>" to the screen.

## Risks
- Bad-value messages echo the offending date/amount text (as AC-10 requires), which could in theory be a description if the config maps columns wrongly.
- Only UTF-8 (with or without BOM) input is supported; other encodings give a one-line error.
- Line numbers are physical file lines (multi-line quoted fields handled by csv reader).
- Date format relies on strptime; two-digit-year formats are accepted if the config says so.
- Windows not tested.
