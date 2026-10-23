# Handoff T1+T2 (developer)
Commits: T1 2b553c0 (core), T2 a9a2128 (CLI, README, examples). Not pushed.
Verify: pytest 26 passed; unittest discover (incl. -k core) OK; spec T2 command OK; package = 297 lines (<=400).
AC->test map: tests/test_core.py (AC-1..8, 10 collection, 13, 16 rules, 17) and tests/test_cli.py (AC-9..12, 14, 15, 16, 4 no-float) - each test docstring names its AC.
Caveats:
- Tests are unittest.TestCase classes (run under pytest and spec's unittest command).
- Tests were written in the same pass as code, not strictly before it.
- Spending is shown as a positive magnitude; category totals are net (negative = spending).
- bad amount/date messages echo the amount/date value (per AC-10 example), never descriptions.
- --out equal to the input CSV is refused; AC-14 import check is a static AST scan plus a socket-blocked run.
- Handoff file left uncommitted (under .autocraft/work).
