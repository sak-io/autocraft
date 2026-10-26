# Evidence: one agent alone vs the starter team, same spec

**Question:** does the autocraft pitch hold up, that a builder who is not the judge of their own work ships better software?

**Short answer from one controlled pair: partly.** A second, critical pass over the work removed most of the defects, for the team and for the solo agent alike. The independent reviewer did **not** beat a solo agent that was told to review its own work harshly. Read [What this does and does not show](#what-this-does-and-does-not-show) before quoting any number below.

## What was run

The same spec ([`SPEC.md`](SPEC.md), Receipt Tally, 17 acceptance criteria), the same model tier (`sonnet`) and the same deliverables (stdlib-only package, tests, examples, README).

| Arm | How it was built |
|---|---|
| **Solo** | One agent did design, code, tests, self-check and the "is it ready?" call. Nobody else looked. Then, as a control, the same agent was resumed once and told to review its own work as a strict outsider and fix what it found. |
| **Team** | The real starter team, installed with `autocraft init . --tool claude-code --team starter --archetype script-automation` (standard token mode): `developer` builds, a fresh `pr-reviewer` reviews (round 1), a fresh `developer` fixes, a fresh `pr-reviewer` re-reviews (round 2, approved), then `release-gatekeeper` runs the release check. |

Both arms were told to work only in their own folder. The solo agent never saw the team's files and the other way round (the harness cannot enforce this; nothing in either transcript suggests otherwise).

**The outside check** ([`outside_check.py`](outside_check.py)) is 55 black-box checks that run `python -m receipt_tally` as a subprocess: 29 checks of the spec's acceptance criteria and packaging goals, plus 26 robustness probes (hostile configs, odd amounts and dates, control characters, `--out` onto the bank file, and so on). It was written from the spec alone and **committed before either build started**. It also passes 55/55 on the existing, reviewed example in `examples/receipt-tally`, which shows it is not asking for the impossible. Severity is fixed per check (MAJOR = crash, data loss, wrong money or privacy; MINOR; NIT).

## Results

[`scores.csv`](scores.csv), raw output in [`raw/`](raw/). "Failed" counts outside-check failures.

| Arm and stage | Checks passed | Failed (MAJOR / MINOR / NIT) | Own tests | Tokens for this step | Tokens so far |
|---|---|---|---|---|---|
| Solo, pass 1 (build) | 48 / 55 | 4 / 2 / 1 | 32 | 68.6k | 68.6k |
| Team, developer build | 46 / 55 | 5 / 3 / 1 | 36 | 77.8k | 77.8k |
| Team, review 1 + fix round 1 (**where lean mode stops**) | 53 / 55 | 1 / 0 / 1 | 45 | 137.5k | 215.3k |
| Team, review 2 (approved; no code change) | 53 / 55 | 1 / 0 / 1 | 45 | 64.0k | 279.3k |
| Team, release-gatekeeper (**blocked**, no code change) | 53 / 55 | 1 / 0 / 1 | 45 | 67.6k | 346.9k |
| Solo, pass 2 (self-review control) | **54 / 55** | 0 / 0 / 1 | 46 | 85.7k* | 154.3k* |

\* The harness reported 85.7k for the resumed solo agent without saying whether that figure is cumulative. If it is per run the solo total is 154.3k; if cumulative it is 85.7k. Either way the solo arm cost less than the team's 215.3k at its lean stopping point. Tokens are as reported by the harness and are not priced.

Time: solo about 3.5 minutes of agent time in two passes, team about 4.7 minutes to the lean stop and 6.5 minutes in total.

### Reading the table

1. **Both first passes shipped real defects.** The unreviewed builds failed 7 and 9 outside checks, 4 and 5 of them MAJOR (a crash on a bad config file, a hostile number printing 666,000 characters, `1.234,56` silently read as 1.23456, sums silently rounded). Neither builder's own tests noticed (32 and 36 green tests).
2. **A critical second pass worked, in both arms.** Team: 46 to 53. Solo: 48 to 54.
3. **The team did not come out ahead.** Its reviewer named 5 of the team build's 9 outside-check failures. A further 2 MAJOR (non-UTF-8 config crash, the 666,000-character number) were not named by either review and went away as side effects of the fix round (a catch-all and a stricter number parser). One MAJOR (1e30-sized amounts silently rounding sums) and one NIT (`1 rows skipped`) **survived both reviews and the release check**. The solo self-review fixed all of them except the NIT.
4. **The reviewers did find things the outside check cannot see.** Both rounds produced findings outside the check's scope: all problem lines lost when every row is bad, `--out --force` able to overwrite the config, raw escape characters still echoed on error lines. The solo self-review also found the last two and not the first.
5. **The release check found no code defect**, but it did catch an unresolved review finding, a missing `docs/STATUS.md` and a README that tells a beginner to install pytest.

All 18 findings: [`findings.csv`](findings.csv). Totals: 7 MAJOR, 7 MINOR, 4 NIT; 12 raised by `pr-reviewer`, 2 by `release-gatekeeper`, 4 only by the outside check. For the 16 where it can be tested, **12 were already present in the solo agent's first pass** (column `solo_first_pass_had_it`; the other 4 were not, and 2 are process items).

## What lean mode costs in quality

Lean mode (see [lean vs thorough](../../docs/lean-vs-thorough.md)) skips the re-review after the fix round, replacing it with the lead re-running the reviewer's probes, and has the lead do the release check instead of a gatekeeper agent.

| Lean trade-off | What the extra step cost here | What it found | Verdict on this run |
|---|---|---|---|
| **Skip the last review round** | 64.0k tokens (+30% on the 215.3k lean total) | 1 real MINOR (raw escape codes on error lines, [TR-11](findings.csv)) and 2 NITs. No outside-check score changed (53 to 53). It also did not find the surviving MAJOR. | **Mattered a little.** A lead re-running round 1's probes would have closed round 1's findings but could not have found TR-11, because it was not in round 1. The cost of missing it: a hostile or corrupt bank file prints escape codes. Small. |
| **Lead does the release check** | 67.6k tokens (+31% on the lean total) | 2 blockers: TR-11 left unresolved, and no `docs/STATUS.md`. 1 gap: the README says to run pytest. No code defect. | **Mattered for docs and loose ends, not for code.** A lead who tracks open review findings and writes `STATUS.md` (the original Receipt Tally lead did) covers the first two. The README/pytest gap is the kind of thing a lead is likely to miss. |

In short: on a local, no-network, single-user tool, lean skipped about 130k tokens (38% of the full team run) and the price was one MINOR and some paperwork. The one MAJOR that survived all of it would also have survived the full process, so it is not a lean-versus-thorough difference. This does not say lean is safe for software with users, logins or money; that needs its own test (ClassBook-sized), which has not been done.

## Findings logs for the existing examples

- [`examples/receipt-tally/findings.csv`](../../examples/receipt-tally/findings.csv): 11 findings (2 MAJOR, 7 MINOR, 2 NIT). The example's README says "2 major, 4 minor, 1 nit" because it groups findings by fix-brief item; the CSV counts distinct defects. Of the 8 where the new solo build allowed a test, **5 were present in the solo first pass, 2 were not, 1 partly**; 3 were not testable.
- [`examples/classbook/findings.csv`](../../examples/classbook/findings.csv): 94 findings (9 MAJOR, 55 MINOR, 30 NIT) extracted from the reviews, QA matrix and audit. The documents state other totals ("21 architecture findings", "9 defects", "3 medium + 7 low"), because they count `[QUESTION]` items, merge duplicates differently or count accepted risks. Every difference is explained in the extraction notes below. `solo_first_pass_had_it` is `untested` for all of them: ClassBook was not rebuilt.

Check totals any time with `python3 scripts/findings_summary.py`; `scripts/validate.sh` validates the files.

ClassBook extraction notes: architecture round 1 has 21 items in the README but 3 are `[QUESTION]`s and are excluded (18 rows; round 2 adds 8); `[QUESTION]` and `[PRAISE]` items are excluded everywhere; QA's D-4 and security L-1/L-6 and M-3 duplicate findings counted at an earlier stage, so they are counted once; accepted risks A-1..A-5 are excluded as the audit itself excludes them; the hardening review's 5 items are all counted although the documents only say "2 minor follow-ups were applied", so 4 are `unknown`.

## What this does and does not show

It shows: a single agent's first pass, with its own tests green, ships crashes and wrong-money bugs that a black-box probe finds in seconds; and a deliberate second look removes most of them.

It does **not** show that independence is what matters:

- **One pair, one run each, one model tier.** The first-pass gap between the arms (48 vs 46) is the size of ordinary run-to-run noise, and the two builders failed different checks.
- **The control was aimed.** My self-review instruction for the solo agent listed hostile-input categories (configs, huge or malformed numbers, control characters, `--out` and `--month` oddities) that overlap with the outside check. The team reviewer got the stock role file, which says "probe the real program" but lists no categories. Part of the solo arm's edge is that its prompt was more specific. This is worth acting on (see below).
- **The outside check is mine.** I wrote it with knowledge of the defect classes found in the earlier Receipt Tally review. It cannot see everything (for example, the reviewers' findings TR-03, TR-07 and TR-11 are outside it).
- **A solo agent that is never asked to review itself is the realistic baseline**, and that arm is the one in the first table row (48/55 with four MAJOR failures). What the experiment shows is that *asking for a second pass* matters; it does not show that a *different* agent doing the second pass matters.
- Not measured: cost in money, quality of the code beyond the check, cross-model review, bigger projects, a human owner.

## What would make this a stronger result

1. Repeat the pair at least 5 times and report the spread, not one number.
2. Give the solo self-review and the team reviewer the same instruction text; vary only who reads it.
3. Add an outside check written by someone who has not seen any earlier review.
4. Try a spec with a planted ambiguity or a design-level trap (ClassBook-style race conditions), where a fresh reader's lack of the builder's assumptions should matter more than on a small CLI.

## Suggested product change

The reviewer missed three things a hostile-input checklist would have prompted for. Add a short, archetype-specific "probe list" (for `script-automation`: config types and encodings, numbers at both extremes, control characters, output paths that alias inputs) to the `pr-reviewer` brief, and re-run this experiment to see whether the reviewer then matches or beats the aimed self-review.

## Reproduce

```bash
python3 evals/receipt-tally/outside_check.py <project_dir> [--json out.json]
```
The prompts given to the agents are in [`prompts.md`](prompts.md). The review and release artifacts are in [`raw/team-artifacts/`](raw/team-artifacts/).
