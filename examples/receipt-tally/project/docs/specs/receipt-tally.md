# Spec: Receipt Tally
Source: `docs/idea.md` (owner: Sam, not a developer, Python 3 on a laptop). Phase: MVP (all of it).

## 1. Goal and non-goals
Goal: Sam runs one command a month on a bank CSV and gets a plain-text spending summary, sorted into categories by rules Sam writes in a text file.
Non-goals:
- No network access of any kind (Sam's data never leaves the laptop).
- No GUI, web page, or app; command line only.
- Never edits, moves or deletes the bank files (read-only).
- No charts, budgets, currency conversion, or bank login/download.

## 2. Acceptance criteria
- AC-1 (layout A) Given a CSV with DD/MM/YYYY dates and one signed Amount column mapped in the config, When run, Then each row becomes a transaction (negative = spending, positive = income).
- AC-2 (layout B) Given a CSV with YYYY-MM-DD dates and separate Debit/Credit columns mapped in the config, When run, Then Debit counts as spending and Credit as income, same result shape as AC-1.
- AC-3 (mapping) Given a different column order/header names, When only the config's column mapping is changed, Then it parses correctly with no code change.
- AC-4 (exact money) Given amounts like 0.10 and 0.20, When totalled, Then the result is exactly 0.30 (Decimal, never float; a test asserts no `float` is used for money).
- AC-5 (first match wins) Given rules in file order, When a description matches several, Then the first matching rule's category is used.
- AC-6 (case-insensitive substring) Given rule `tesco = Groceries`, When description is "CARD PAYMENT TO TESCO STORES", Then category is Groceries.
- AC-7 (uncategorised) Given a description matching no rule, When run, Then it is placed in the "Uncategorised" bucket and counted.
- AC-8 (month summary) Given a month `--month YYYY-MM` (default: latest month in the file), When run, Then output shows per-category totals, total income, total spending, net, the 5 largest spends (date, amount, description) and the uncategorised count.
- AC-9 (missing file) Given a path that does not exist, When run, Then a one-line plain error is printed, exit code is non-zero, no traceback.
- AC-10 (bad row) Given a row with a bad date/amount/missing field, When run, Then a line like `line 7: bad amount 'abc'` is reported, the row is skipped, other rows are still processed, and exit code is 0 with a "N rows skipped" note.
- AC-11 (dry-run default) Given no `--out`, When run, Then the summary goes only to the screen and no file is created or changed anywhere.
- AC-12 (`--out`) Given `--out report.txt`, When run, Then the summary is written to that file (and only that file); an existing file is not overwritten without `--force`.
- AC-13 (deterministic) Given the same inputs, When run twice, Then outputs are byte-identical (stable sorting, ties broken by date then description; no timestamps in output).
- AC-14 (no network) Given the test suite, When the tool runs with sockets blocked (test patches `socket.socket` to raise), Then it still succeeds; a test also asserts the package imports no networking modules.
- AC-15 (input untouched) Given the bank file, When run, Then its bytes and modified time are unchanged.
- AC-16 (privacy) Given any run, When errors/warnings are printed, Then they cite line numbers and field names but never transaction descriptions; no log files are written.
- AC-17 (readable output) Given any run, When output is viewed, Then it is plain aligned text with no colour/ANSI codes and meaning does not depend on colour.

## 3. Non-functional goals
| Area | Goal | How checked |
|---|---|---|
| Privacy | No network; no logs or error text containing descriptions | AC-14, AC-16 |
| Simplicity | Python 3 stdlib only, one package, <= 400 lines of code (excluding tests) | `verify` line count check |
| Token efficiency | Whole project built within lean budget: spec <=35k tokens; T1 and T2 each one developer pass plus <=2 review rounds | Orchestrator logs |
| Accessibility | Plain text, aligned columns, readable without colour or a screen | AC-17 |
| Correctness | Money exact to the cent | AC-4 |

## 4. Design
Package `receipt_tally/` (stdlib only: `csv`, `decimal`, `datetime`, `argparse`, `tomllib`/simple parser):
- `config.py`: load config file into `Config` (column mapping + rules).
- `parse.py`: read CSV -> `(transactions, problems)`.
- `rules.py`: `categorise(description, rules) -> str`.
- `summary.py`: build `Summary` and `render(summary) -> str`.
- `cli.py` / `__main__.py`: argparse, I/O, exit codes. Only place that touches files or the screen.

Data shapes:
- `Transaction(date: datetime.date, amount: Decimal, description: str)`; amount signed, negative = spending (Debit stored as negative, Credit as positive).
- `Problem(line: int, message: str)`; `Rule(pattern: str, category: str)`.
- `Summary(month, by_category: dict[str, Decimal], income, spending, top5, uncategorised_count, skipped)`.

Config: one TOML file (Sam edits it in a text editor; rules are one per line in a list, order = priority):
```toml
[columns]            # layout B example; layout A uses amount = "Amount"
date = "Date"
date_format = "%Y-%m-%d"      # layout A: "%d/%m/%Y"
description = "Description"
debit = "Debit"
credit = "Credit"
# amount = "Amount"           # use instead of debit/credit
[rules]
list = ["tesco = Groceries", "shell = Transport", "salary = Income"]
```
Usage: `python -m receipt_tally bank.csv --config rules.toml [--month 2026-09] [--out report.txt [--force]]`.

Errors: parse problems collected (not raised) and shown after the summary; unrecoverable ones (missing file, bad config, unknown column) raise a `UserError` caught in `cli.py` -> one-line message, exit 2. Parsing amounts: strip currency symbols/thousands separators, `Decimal(str)` only. Output encoding utf-8; input read with `utf-8-sig`.

## 5. Tasks
- T1 core: config, parse (both layouts), rules, summary, render. Covers AC-1..AC-8, AC-10 (collection of problems), AC-13, AC-16 (core), AC-17. verify: `python -m unittest discover -s tests -k core` (fixtures: two sample CSVs, one with a bad row).
- T2 CLI, errors, docs: argparse, `--month`, `--out/--force`, exit codes, README (plain-language, for Sam, with both config samples), no-network and read-only tests. Covers AC-9, AC-10 (CLI output), AC-11, AC-12, AC-14, AC-15, AC-16, AC-17. verify: `python -m unittest discover -s tests && python -m receipt_tally tests/fixtures/a.csv --config tests/fixtures/a.toml && wc -l receipt_tally/*.py` (total <= 400).
- T3 (optional, only if Sam asks): `--year` roll-up or CSV export of the summary. Covers none of AC-1..17. verify: new tests plus the T2 command.

## 6. Open questions (do not block; defaults apply)
- Q1: Which currency symbol, if any, should output show? Default: none, plain numbers with 2 decimals.
- Q2: Should refunds (positive amounts in a category) reduce that category's total? Default: yes, categories show net; income/spending totals split by sign.
- Q3: Config format TOML (above) vs. plain `rules.txt`? Default: TOML, since the column mapping needs structure; rules are still one line each.
