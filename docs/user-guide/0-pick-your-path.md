# Pick your path

Which commands to run depends on what you are building. Find your row, run the commands, then follow the page it points to. Every path keeps the same fixed points: tests with every change, an independent review, and a human who merges.

First, get autocraft once:

```bash
git clone https://github.com/sak-io/autocraft ~/autocraft
```

If you are not sure what kind of software you have, ask for a recommendation first (it only prints, it changes nothing):

```bash
python3 ~/autocraft/bin/autocraft recommend "<your idea in a sentence or two>"
```

## At a glance

| Your project | Team | Typical extras | Worked example | Read next |
|---|---|---|---|---|
| **Simple**: static site, script, scheduled job, small command-line tool | `starter` | `--token-saver` | [Receipt Tally](../../examples/receipt-tally/README.md) | pages 1, 2, 3 |
| **Medium**: web app or API with a few features and a database | `starter` plus roles, or `web-product` / `api-backend` | `--capability` for auth, database, payments | between the two examples | pages 3, 4, 5 |
| **Complex**: several user types, accounts, email, payments, a release gate | `starter` plus `architect`, `principal-engineer`, `qa-engineer`, `release-gatekeeper` | `--capability ...`, `--autonomy 1` or `2` | [ClassBook](../../examples/classbook/README.md) | pages 3, 4, 5, then [guardrails](../guardrails.md) |
| **Existing codebase** | `starter` plus `architect`, `qa-engineer` | `--experience expert`, `--commit` | none | [page 6](6-for-software-engineers.md) |
| **Written documents first** (concept, technical plan) | any | none | [Pantry Pal kickoff](../../examples/pantry-pal-kickoff/README.md) | [kickoff from your documents](../kickoff-existing-docs.md) |
| **Idea only, no idea where to start** | decided by `discover` | none | none | [bootstrap prompt](../bootstrap-prompt.md) |

`recommend` suggests these for common ideas: a bakery website maps to `static-site`, a photo-renaming script to `script-automation`, and "online ordering plus an iPhone app" to `fullstack-app` with database, payments and authentication.

## Simple: a site, a script or a small tool

The `starter` team is enough: a requirements analyst, a developer, an independent reviewer and a security auditor. Add `--token-saver` to run the reviewer, auditor and analyst on a mid-tier model, with two review rounds.

```bash
mkdir my-tool && cd my-tool && git init
python3 ~/autocraft/bin/autocraft init . --tool claude-code --team starter \
  --archetype script-automation --token-saver
python3 .autocraft/framework/bin/autocraft doctor
```

Then open your AI tool in that folder and run `/start` with your idea. Use `--archetype static-site` for a website.

What you can skip: a separate architect, QA engineer, release gatekeeper and parallel developers. What you should not skip: the written spec with acceptance criteria, the tests, and the independent review. In Receipt Tally the reviewer found 2 major and 4 minor issues after the developer had finished, with 4 agent runs in total.

Set a budget before you start, for example "at most 5 agent runs". It is an instruction to the agents, not a hard stop (see [guardrails](../guardrails.md), gap 4).

## Medium: a web app or an API

Two ways to get there:

```bash
# A. The starter team with the roles this size of project usually needs
python3 ~/autocraft/bin/autocraft init . --tool claude-code --team starter \
  --archetype web-app --capability authentication,database \
  --add-role architect,qa-engineer

# B. A ready-made bigger team
python3 ~/autocraft/bin/autocraft init . --tool claude-code --team web-product \
  --archetype web-app --capability authentication,database
```

Use `api-backend` instead of `web-product` for an API, a scheduled job or an event processor. Add `--token-saver` if you want the cost levers described in [lean vs thorough](../lean-vs-thorough.md).

Keep `autonomy_level` at 1 or 2 so you approve the spec, the architecture and every merge. Page 4 shows how to read reviews and change your mind part-way through.

## Complex: several features, accounts, email, payments

This is how ClassBook was set up (a booking app with accounts, email and a release check):

```bash
python3 ~/autocraft/bin/autocraft init . --tool claude-code --team starter \
  --archetype fullstack-app --capability authentication,database,email-and-notifications \
  --add-role architect,principal-engineer,qa-engineer,release-gatekeeper --experience beginner
```

Expect more agent runs: a spec, an architecture with review rounds, one task per feature, QA, a security audit and a release check. The ClassBook build used 26 agent runs (about 2.2 million tokens) for an app of roughly 2,400 lines with 539 tests. Its final round used lean mode and took about 190 thousand tokens. See [lean vs thorough](../lean-vs-thorough.md) for a side-by-side comparison, which is not like for like.

For money, accounts and personal data, read [guardrails](../guardrails.md) first and turn on branch protection (`scripts/onboard-repo.sh`). Most guardrails are instructions; branch protection and CI are what a tool enforces.

## An existing codebase

```bash
cd your-repo
python3 ~/autocraft/bin/autocraft init . --tool claude-code --team starter \
  --add-role architect,qa-engineer --experience expert --commit
```

`--commit` makes the install one dedicated commit. [Page 6](6-for-software-engineers.md) covers pointing the team at your design documents, one pull request per task and per-role models.

## Using the lean task board (`/lean-build`)

`/lean-build` is installed by every team except `setup`. It runs several agents from a small task board that any AI tool can read. The workflow installs the board itself the first time you run it. To do that step yourself:

```bash
python3 .autocraft/framework/bin/autocraft board init
```

Projects installed before `/lean-build` was added to the teams can copy the workflow in by hand:

```bash
mkdir -p .autocraft/custom/workflows
cp ~/autocraft/workflows/lean-build.md .autocraft/custom/workflows/
python3 .autocraft/framework/bin/autocraft sync
```

See [lean orchestration](../lean-orchestration.md) for how the board works.

## Things that apply to every path

- You approve the decisions that are yours; agents never merge into `main`.
- `autocraft doctor` checks that the install is complete.
- Cost depends on your tool, plan and project. Treat figures from the examples as one data point, and record your own per-run tokens.
- Something unclear? Run `/explain`, or see the [FAQ](7-faq-and-troubleshooting.md).
