# Lean or thorough? Two real builds, side by side

Two examples in this repo were built with the same framework and the same safeguards (written spec, tests with every change, a *different* agent reviewing and probing, a human owner who decides and merges). They differ in **how much process and how many tokens** were spent:

| | [ClassBook](../examples/classbook/README.md) (thorough) | [Receipt Tally](../examples/receipt-tally/README.md) (lean) |
|---|---|---|
| What it is | Web app: accounts, bookings, admin, emails, race conditions | Local command-line tool: bank CSV to monthly summary |
| Team | 7 roles used (analyst, architect, principal engineer, developers, reviewers, QA, security auditor) | 4 roles (analyst, developer, reviewer, security-auditor installed, scanner run instead) |
| Setup | `standard` mode (lean added for the last round only) | `--token-saver` (`token_mode: lean`) from the first minute, with a budget stated up front |
| Agent runs | 26 | **4** |
| Tokens | ≈ 2.20 M | **≈ 0.27 M** |
| Tool calls by agents | 386 | **27** |
| Acceptance criteria | 34 | 17 |
| Application code / tests | 1,636 / 3,977 lines; 539 tests | 274 / 392 lines; 36 tests |
| Independent review found | architecture: 21 findings; a major test gap; a crash on huge IDs; weak email tests; later QA: 9 defects; audit: 3 medium + 7 low | 2 MAJOR + 4 MINOR + 1 NIT (crashing config, 100,000-digit number, totals that did not add up, control characters on screen, a test that missed a mutation) |
| Mutation probes | 21 + 19 deliberate breakages, all caught | 3 deliberate breakages: 2 caught, 1 survived (a missing test), then added and re-checked |
| Left undone | Deployment (needs the owner's host sign-up) | Nothing (it is a local tool) |

## Normalised, so the sizes don't mislead

| | ClassBook | Receipt Tally |
|---|---|---|
| Tokens per acceptance criterion | ≈ 65 k | **≈ 16 k** |
| Tokens per line of application code | ≈ 1,340 | **≈ 990** |
| Tokens per test | ≈ 4,100 | ≈ 7,500 |

Read the last row honestly: Receipt Tally spent *more* per test, because a fixed cost (spec, brief, review) is spread over a much smaller project. **The two projects are not like-for-like**, and this table does not prove "lean is 8x cheaper" for the same job. It shows that a small project does not need to pay the cost of a big one, and where the money goes.

## Where ClassBook's 2.2 M went

| Phase | Tokens | Share |
|---|---|---|
| Spec, architecture, principal-engineer challenge (7 runs) | 296 k | 13% |
| Build and review of 6 tasks, incl. fix rounds (15 runs) | 1,221 k | 56% |
| Independent QA (321 k) + security audit (170 k) | 491 k | 22% |
| Hardening and final review, **run in lean mode** (2 runs) | 188 k | 9% |

- Developers: 859 k. Reviewers: 549 k. About a quarter of all tokens were reviewers.
- The single most expensive run was the QA pass (321 k, 65 tool calls), and it earned its cost: 177 tests, 21 mutation probes, 9 defects found.
- **The lean round inside ClassBook was not cheaper per item:** it fixed 13 items (9 defects, 4 security issues), added 18 regression tests and had them independently reviewed for 188 k, about 14 k per item. T4's ordinary fix round plus re-review cost about 6 k per item (31 k for 5 findings). The lean round did more per item (security fixes, regression tests, probing review), and a fix round is cheap either way. Lean mode helped most where whole phases could be skipped or merged, not in shaving a fix round.

## What the lean levers were, and what each did

| Lever (see [protocol section 15](protocol.md)) | Receipt Tally | Effect |
|---|---|---|
| **Brief, don't re-explore** | One brief file per run; agents read only what it named | Every run finished in 5-8 tool calls (ClassBook runs averaged 15) |
| **Batch related work** | T1 and T2 built in one pass; no separate architect (design lives in the spec) | 2 fewer runs, 1 fewer handoff |
| **Depth follows risk** | Reviewer ran code against money, dates, privacy, read-only; skimmed the rest | The 2 MAJORs were found where the risk was |
| **Automated checks first** | Tests and the code scanner by the lead, no model tokens | Free |
| **Fresh with a brief beats resumed** | Fix round was a new agent with a fix brief | No long history re-read |
| **Mid-tier model** (`--token-saver`) | `sonnet` for all four runs | Lower price per token; not measured here, so no saving is claimed in the numbers above |
| **Bounded runs, short reports** | Token and tool-call caps in every brief, replies of 8-15 lines | Lead's context stayed small enough to run the whole project in one sitting |
| **Mechanical verification instead of a 3rd review** | Lead re-ran the reviewer's probes and the surviving mutation | Closed the loop for about 0 tokens |

## What lean did NOT cut

Same in both: a written spec with testable criteria, tests with every behaviour, a different agent reviewing, review findings sent back and fixed, a human owner approving. Lean removed *roles and depth where the risk was low*, not the gates.

## What lean skipped, and when you should not skip it

Receipt Tally had no architect, no principal-engineer challenge, no QA matrix, no threat model, no separate security audit (a code scanner and a privacy test were used). That is right for a local tool with no network, no accounts and no other users. **It would be wrong for ClassBook**: its race conditions, sign-in, session and admin protection are exactly what the architecture challenge, the 50-simultaneous-bookings test and the audit found problems in. A rule of thumb:

| If the software... | Use |
|---|---|
| runs only on your machine, has no accounts, no money, no shared data | **lean** (`--token-saver`, starter team, 1 reviewer) |
| has users, logins, stored personal data, or is on the internet | lean mode **plus** an architect, QA and a security audit; lean only for the fix rounds |
| handles money, health or safety | thorough; spend the tokens |

## How to get the saving on your own project

```bash
autocraft init . --tool claude-code --team starter --token-saver     # or: --token-mode lean on any team
```
Then, before the first agent runs, write down a budget (runs and tokens) and log each run in an `agent-runs.csv`, as both examples do. Both overran or came close: Receipt Tally was ≈8% over its stated 250 k; measuring is what made that visible.

**Caveat on evidence:** these are two single runs by one team lead, with a simulated owner. They show the levers work and where tokens go, not a controlled benchmark.
