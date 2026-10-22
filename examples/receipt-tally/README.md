# Example: Receipt Tally, built effectively with a small token budget

A second worked example, the opposite of [ClassBook](../classbook/README.md): ClassBook shows a thorough multi-agent build of a web app (24 agent runs, ≈2.0M tokens). **Receipt Tally shows the same safeguards (spec, tests, an independent reviewer that probes, human-owned decisions) on a small tool, with `token_mode: lean` from the first minute.**

The owner's idea, in their words ([`project/docs/idea.md`](project/docs/idea.md)): *"a small tool that reads the CSV files my bank lets me download, sorts each transaction into categories using rules I write in a text file, and prints a monthly spending summary. It must never send my data anywhere."*

## Result against the budget

The budget was set **before** starting: at most 5 agent runs and about 250k tokens.

| | Planned | Actual |
|---|---|---|
| Agent runs | ≤ 5 | **4** ([`agent-runs.csv`](agent-runs.csv)) |
| Tokens | ≈ 250k | **≈ 270k** (spec 59k, build 73k, review 70k, fixes 68k), about 8% over |
| Agent time | | ≈ 5 minutes |
| Result | | 274-line stdlib-only package, **36 tests pass**, 17 acceptance criteria, code scan clean, independent review found 2 MAJOR + 4 MINOR issues, all fixed and re-verified |

That is about **one eighth of ClassBook's tokens** (the app is far smaller, so this is not a like-for-like claim; the point is where the tokens went and what was *not* spent).

## How it was done (about 10 lines of commands)

```bash
autocraft recommend "<the idea>"          # free; it could not classify this idea (see "what went wrong")
autocraft init . --tool claude-code --team starter --archetype script-automation --token-saver
```
`--token-saver` = reviewer/analyst/auditor on a mid-tier model, 2 review rounds, 2 parallel developers, plus `token_mode: lean`. The team is only 4 roles: `requirements-analyst`, `developer`, `pr-reviewer`, `security-auditor`.

| # | Who | Brief | Output |
|---|---|---|---|
| 1 | requirements-analyst | [`.autocraft/work/spec/brief.md`](project/.autocraft/work/spec/brief.md): one file, ≤120 lines, ≤3 tasks, ≤3 open questions with defaults | [spec](project/docs/specs/receipt-tally.md) (design and task list inside, no separate architect for a tool this size) |
| (owner) | Sam (simulated) | accepted the three default answers (no currency symbol, refunds reduce totals, TOML config) | 0 extra tokens |
| 2 | developer | [`.autocraft/work/T1/brief.md`](project/.autocraft/work/T1/brief.md): read only the spec, build **both tasks in one pass**, tests map to AC numbers | package, 26 tests, README |
| 3 | pr-reviewer (fresh) | risk-tiered: probe money, dates, privacy and read-only guarantees by running code; only read the diff for the rest; 3 mutation checks | [review](project/.autocraft/work/T1/review.md): CHANGES-REQUESTED |
| 4 | developer (fresh) | [`fix-brief.md`](project/.autocraft/work/T1/fix-brief.md): each finding red-then-green | 10 more tests |
| (lead) | verification | re-ran the reviewer's probes and the surviving mutant by hand instead of paying for a third review | all closed |

## What kept the cost down

1. **One precise brief per run**, each telling the agent what to read and what not to; every agent finished in 5–8 tool calls.
2. **Batching:** two tasks, one build pass; the architect role was skipped and the design lives inside the spec.
3. **Risk-tiered review:** the reviewer ran code against money, dates and privacy and only skimmed the rest.
4. **A fresh agent with a fix brief** instead of resuming a long conversation.
5. **Mechanical verification** (re-running the reviewer's probes) in place of another review round.
6. **Free tools first:** tests and the code scanner cost no model tokens.

## What the review caught that the builder missed

Config files that crash with a traceback; a number like `1E+100000` that printed 100,000 digits; sub-cent amounts that made printed lines not add up to the total; a silent all-zero summary for `--month 2026-3`; an escape character in a transaction description reaching the terminal; and a thousands-separator mutation that no test noticed. Without the independent reviewer these would have shipped.

## What went wrong, honestly

- **About 8% over the token budget.** Review plus fixes (≈138k) cost more than the build (73k). Writing the tests in the same pass as the code, rather than first, probably made the review heavier.
- **`autocraft recommend` could not classify the idea** ("couldn't tell the kind of software") and fell back to the lean team. The archetype (`script-automation`) was picked by the lead. Worth improving the recommender's keywords.
- **One test cannot prove its purpose:** the sum-precision test passes with or without the larger Decimal context.
- **The release check was done by the lead** from the evidence, not by a separate gatekeeper agent (see [`project/docs/STATUS.md`](project/docs/STATUS.md)).

## Run it

```bash
cd examples/receipt-tally/project
python -m receipt_tally examples/bank_layout_a.csv --config examples/config.toml
python -m pytest -q          # needs pytest; 36 tests
```
