# Fix brief round 2 (lean: <=40k tokens, <=20 tool calls, reply <=8 lines). Read ONLY .autocraft/work/T1/review.md, then the files you edit.
Fix, each with a test that fails before the fix (red then green):
1. [MAJOR] Bad config must never traceback: wrong types (date_format = 5, etc.), non-UTF-8 config, missing keys -> one-line error, exit 2.
2. [MAJOR] Amount bounds: reject non-finite/exponent forms (`1E+100000`, NaN, Infinity) and absurdly large amounts (|x| >= 10**12) as a bad-row line; make sure Decimal context cannot silently round sums (use a context with enough precision).
3. [MINOR] Reject amounts with more than 2 decimal places (bad row), so printed lines always add up. Reject ambiguous European format like `1.234,56` as bad row.
4. [MINOR] `--month` must be strictly YYYY-MM (error exit 2 otherwise); when the month has no rows print one line saying so.
5. [MINOR] Strip control characters (ESC etc.) from anything printed from the CSV; refuse `--out` when the path is a dangling symlink.
6. [MINOR] Add the missing test with a quoted "1,234.50" amount (kills the thousands-separator mutant).
7. [NIT] "1 rows skipped" -> proper plural.
Keep package <=400 lines, stdlib only. Run all tests. Commit as one commit "T1/T2 review round 1 fixes". Update README only if behaviour text changed. Do not push.
