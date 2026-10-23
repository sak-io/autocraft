# T1/T2 review (pr-reviewer, independent) - commits 2b553c0, a9a2128
Ran: 26 tests pass; 297 code lines (<=400); stdlib only, no network imports (argparse/csv/datetime/decimal/os/sys/tomllib); no print of descriptions except spec-mandated top-5.
Probed OK: debit/credit signs, refund netting (income/spending/net reconcile with categories), "-1,234.50" parsed, 31/02 -> `bad date`, BOM+CRLF, empty file, header-only, extra/short columns, unicode, 200k-char field, NUL, invalid UTF-8 (all one-line error or skipped row, no traceback), missing file rc=2, --out == input via symlink or `sub/../a.csv` refused, input md5 unchanged, no-overwrite without --force.

[MAJOR] Uncaught tracebacks on bad config: `date_format = 5` -> TypeError in strptime; non-UTF-8 config file -> UnicodeDecodeError (load_config catches only TOMLDecodeError/OSError). Spec: bad config -> UserError, exit 2. Validate str types in config.py and catch UnicodeDecodeError.
[MAJOR] Huge exponent amount `1E+100000` is accepted (Decimal) and render prints a ~100k-digit number (hang/garbage on one hostile or corrupt cell). Reject exponent forms / cap magnitude in parse_amount (also prec-28 context silently rounds sums of >28-digit values).
[MINOR] Sub-cent amounts accepted: three `-0.005` rows show 0.00 each but total 0.01 (half-even rounding), so displayed lines do not add up. Reject >2 decimals or quantize at parse.
[MINOR] `--month 2026-3` passes validation (strptime lenient) but matches nothing: silent all-zero summary. Normalize to %Y-%m. Also valid month with zero rows gives no "no transactions" note.
[MINOR] European "1.234,56" silently becomes 1.23456 (comma stripped); wrong money with no warning. Reject/skip if result has >2 dp (same fix as above).
[MINOR] Descriptions with ESC bytes are echoed raw in top-5 (AC-17 "no ANSI"); strip control chars on render. Dangling-symlink --out writes through to its target (minor).
[NIT] "1 rows skipped" grammar; problem line number for multi-line quoted field is the record's last line.
[NIT] README accurate to CLI behaviour (checked flags, messages, rc). Output deterministic (sorted ties).

Mutation probe (5 mutants in /tmp copies, deleted):
 killed: debit sign flip; rules reversed (first-match); float(Decimal(str(float()))) money.
 SURVIVED: removing "," from thousands-strip set (tests never feed "1,234.50"); `<=`/`>=` in income/spending split (equivalent for zero amounts, benign).
 -> Add a test for quoted thousands separator.

Verdict: CHANGES-REQUESTED (two MAJORs: config tracebacks, huge-exponent amounts; plus thousands-separator test gap).
