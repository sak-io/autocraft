# 6. For software engineers

You write software for a living. You don't need the "what is a pull request" tour — you need to know what this is, what it will and won't do to your repo, how far you can bend it, and where to trust it less. This page is the compressed, engineer-first version of the guide.

## The model in six lines

- A **role** is a markdown file (frontmatter: `id`, `title`, `category`, `abilities`, optional `model`, `description`; body = the job, inputs, outputs, checklist, rules, handoff). 22 ship in [`roles/`](../../roles/).
- A **team** is a roster plus a playbook ([`teams/`](../../teams/)); a **workflow** is a procedure with `needs: [roles]` ([`workflows/`](../../workflows/)) — workflows switch on automatically when their roles are present.
- **Archetypes** (20 software types) and **capabilities** (10 cross-cutting concerns: auth, payments, database, …) are domain checklists that roles read as requirements.
- The **[protocol](../protocol.md)** is the contract between roles: handoff blocks, severity-tagged reviews, round limits, human gates, label state machine, `gh` vs. GitHub-tools mapping, git modes.
- Your project holds only **config** (`.autocraft/config.yml`) and **overlays** (`.autocraft/custom/`). Everything under `.claude/`, `.cursor/`, `AGENTS.md`, … is **generated**; `autocraft sync` regenerates it, `autocraft doctor` flags drift.
- One neutral source, nine exporters (Claude Code, Claude app, Cursor, Copilot, Gemini CLI, Windsurf, Cline, `AGENTS.md`, plain prompts).

## Fast path in an existing repo

```bash
git clone https://github.com/sak-io/autocraft ~/autocraft
cd your-repo
python3 ~/autocraft/bin/autocraft recommend --file docs/design.md            # optional: first-guess team + design-risk flags
python3 ~/autocraft/bin/autocraft init . --tool claude-code --team starter \
    --add-role architect,qa-engineer --experience expert --autonomy 2 \
    --sources docs/design.md --git-mode pr-per-task --owner your-github-handle --commit
```
`--commit` makes the installation **one dedicated commit** (`chore(autocraft): install agent team (generated files)`) containing only autocraft-owned paths, staged by explicit pathspec, so anything else you have staged or modified is left exactly as it was; hooks run, nothing is pushed. Later `autocraft sync --commit` does the same for regenerated files. Generated files are marked `linguist-generated` in `.gitattributes` (a managed block; `--no-gitattributes` opts out), so GitHub collapses them in pull requests. See [reviewing large PRs](../reviewing-large-prs.md).

What lands in your repo: `.claude/agents/` and `.claude/skills/` (or your tool's equivalents), a managed block in `CLAUDE.md` (your own text is preserved), `.autocraft/` (config, manifest, protocol, selected profiles, a **vendored copy of the framework** ≈ 0.9 MB so sessions never need access to this repo), and `.claude/settings.json` pre-approving routine safe commands — **read it after the install commit and change it if you disagree**; `sync` never overwrites it. Nothing is installed globally; `rm -rf` the generated paths to remove it.

`--experience expert` makes agents terse and trade-off-oriented. `--git-mode pr-per-task` gives one branch and PR per task with `agent:*` labels; the default `session-branch` keeps everything on one branch (better in cloud sessions).

## Pick and choose

**À la carte.** Start from any team and add/remove roles:
```bash
autocraft list roles | list teams | list workflows | list archetypes | list capabilities
autocraft init . --team starter --add-role security-auditor --remove-role requirements-analyst
autocraft add-role qa-engineer        # later
autocraft remove-role ux-designer
```

**Your own team** — a file in your repo, same format as the built-in teams:
```markdown
<!-- .autocraft/custom/teams/review-bench.md -->
---
id: review-bench
name: Review Bench
summary: We write the code; agents review, probe and audit it.
roles: [pr-reviewer, qa-engineer, security-auditor]
workflows: [review-pr, security-scan]
---
# Playbook
Humans author changes. `pr-reviewer` reviews each PR in a fresh context and runs the tests;
`qa-engineer` adds missing tests for the acceptance criteria; `security-auditor` runs before release.
```
```bash
autocraft init . --team review-bench     # or combine: --team review-bench,mobile
```

**Per-role model (Claude Code).** Spend where it matters — e.g. a cheaper model for a high-volume reviewer, the strongest for the architect:
```bash
autocraft init . --role-model pr-reviewer=sonnet,qa-engineer=haiku,architect=opus
```
(or `role_models: [pr-reviewer=sonnet]` in the config). Default is `inherit` — the session's model.

**Permissions per role.** A role's `abilities` (`read, search, write, edit, shell`) become that tool's tool allow-list (e.g. reviewers have no `write`/`edit`). Override by replacing the role (below).

## Customize — from lightest to heaviest

| Level | How | Use for |
|---|---|---|
| 1. Knobs | `.autocraft/config.yml`: `autonomy_level`, `max_review_rounds`, `max_parallel_developers`, `git_mode`, `experience`, `role_models` | strictness, parallelism, verbosity |
| 2. House rules for everyone | `.autocraft/custom/team-rules.md` | conventions: commit style, lint/format commands, layering rules, forbidden libraries, test pyramid |
| 3. House rules for one role | `.autocraft/custom/roles/<id>.append.md` | "reviewer: flag any new dependency"; "developer: use our error type" |
| 4. Replace a role | copy `.autocraft/framework/roles/<id>.md` to `.autocraft/custom/roles/<id>.md` and edit | different checklist, different `abilities`/`model` |
| 5. New role | `autocraft new-role <id>`, then `add-role` | `migration-reviewer`, `perf-engineer`, `compliance-reviewer` |
| 6. New/changed workflow | `.autocraft/custom/workflows/<id>.md` (`id`, `description`, optional `needs`) | your release ritual, your triage flow |
| 7. Your own team | `.autocraft/custom/teams/<id>.md` | a roster nobody ships |
| 8. Fork | change `roles/`, `teams/`, profiles in a fork, then `python3 <fork>/bin/autocraft sync .` | org-wide standards |

Example `team-rules.md` (plain English is the interface):
```markdown
- Go 1.23, no CGO. `make lint test` must pass before any handoff; paste the tail of the output.
- Conventional commits. One logical change per commit.
- Domain code may not import `internal/transport`. If you need to, stop and raise it as [QUESTION].
- New dependencies need an ADR (docs/adr/) with the alternative you rejected.
- Never touch `/migrations` without the `migration-reviewer` role.
```
After any edit: `autocraft sync && autocraft doctor`. Generated files are overwritten (and flagged if hand-edited), so changes belong in `custom/`.

## What the loop actually enforces

- **Builder ≠ reviewer.** Reviews run in a **fresh agent** that must run the tests itself, probe the change (the ClassBook reviewers started real servers, replayed DST edge cases, and *mutated the code* to see whether the tests would notice), and answer in severity-tagged findings. Authors must answer every finding; reviewers re-verify each one; after `max_review_rounds` it escalates to you.
- **Contracts live in files**, not chat: spec with acceptance criteria → architecture/ADRs → work breakdown → `.autocraft/work/<task>/handoff-N.md` and `review-N.md` → `docs/STATUS.md`. Any session (or human) can pick up from the repo.
- **You hold the merge.** In `pr-per-task` mode agents open PRs, never merge. In `session-branch` mode they never touch `main` or open a PR unless asked.
- **Parallelism with isolation**: independent tasks run in separate `git worktree`s; the lead integrates reviewer-approved branches and re-runs the *whole* suite (in the example, two individually-approved branches broke each other on merge — caught by that step).

**Trust, but verify.** Agents' claims are claims. Read the diffs and the review files, run CI, and spot-check tests by breaking the code. In the ClassBook example the QA role found defects that per-task reviewers had approved, and the independent security audit found a disk-fill issue no earlier review had flagged — roles are cheap insurance, not a substitute for your own review of anything you'll ship.

## Fitting your workflow

- **PRs and branch protection.** `git_mode: pr-per-task` + the optional GitHub module (`autocraft github . --lang python`: CI, CodeQL/Dependabot/secret scanning, labels, templates; `scripts/onboard-repo.sh` also applies branch protection and reads each control back).
- **Keep the generated files honest in CI:**
  ```yaml
  - run: python3 .autocraft/framework/bin/autocraft sync
  - run: test -z "$(git status --porcelain)"          # generated files match config + custom/
  - run: python3 .autocraft/framework/bin/autocraft doctor
  ```
- **Mixed tools on one team.** `--tool claude-code,cursor,agents-md` gives everyone the same roster in their own tool's format.
- **Monorepos.** One `.autocraft/` per repo root. Declare several archetypes (`[mobile-app, api-service]`); the architect tags tasks by component. There is no per-subdirectory team yet.
- **Cost.** Independent roles re-read context, so a team spends more tokens than one agent (ClassBook ≈ 2.2 M tokens, QA ≈ 16 % of it, and QA found 9 defects). Start lean (`--token-saver`), add roles where you've seen failures, use `--role-model` for high-volume roles. See [guardrails](../guardrails.md) for what the cost controls do and do not enforce.

## Extend and contribute

| Add | File | Checked by |
|---|---|---|
| Role | `roles/<id>.md` (+ list in a team) | `scripts/validate.sh` (frontmatter, abilities) |
| Team | `teams/<id>.md` | roles/workflows exist; every archetype covered by some team |
| Workflow | `workflows/<id>.md` (`needs:`) | exists; description |
| Archetype / capability | copy a profile, keep its headings | required headings; listed in the catalog |
| Tool exporter | an `export()` branch in `bin/autocraft`, `TOOLS`/`HOWTO` entries, `docs/tools/<tool>.md` | validate generates, parses and re-syncs every exporter |
| Language CI | `templates/github/workflows/ci-<lang>.yml` + `LANGS` | validate |

`bin/autocraft` is one stdlib-only Python file (no installs). Details: [customizing](../customizing.md).

## Known limits

- Only the **Claude** path has been exercised end to end; the other exporters follow documented formats but haven't been run in those products.
- Custom **archetypes/capabilities** per project aren't supported yet — encode your standards in `team-rules.md` or a custom role.
- `recommend` is a keyword heuristic, not an analysis; the Team Builder (an agent) reads your documents properly.
- Model overrides apply to Claude Code only. Agents can be wrong, confidently; the process reduces and surfaces errors, it doesn't remove them.

**Next:** [7. FAQ and troubleshooting →](7-faq-and-troubleshooting.md)
