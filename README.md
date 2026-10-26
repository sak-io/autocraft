# autocraft

![validate](https://github.com/sak-io/autocraft/actions/workflows/validate.yml/badge.svg)

**Agent teams for building software with AI.** Pick your kind of software, pick your AI tool, get a ready-made team of specialised agents — planner, designer, builders, independent reviewer, QA, security, release check — that you can use as is, trim, or rebuild to your own standards. You approve the decisions that matter and always hold the merge.

Claude is the first-class target (Claude Code in a terminal, and Claude app Code sessions on web and phone). The same team exports to Cursor, GitHub Copilot, Gemini CLI, Windsurf, Cline, anything that reads `AGENTS.md`, or plain prompts.

---

## Why

Building with *one* AI agent doing everything — planning, coding, and judging its own work — works until it doesn't: mistakes go unnoticed, context gets muddled, nobody holds the quality bar. Professional teams solve this with **roles and checkpoints**. autocraft gives you that structure as AI agents, as plain files in your repo:

| One agent does everything | An autocraft team |
|---|---|
| Reviews its own work | A *different* agent reviews, in a fresh context, and must run the tests itself |
| One long, muddled context | Each role carries only what it needs |
| Tests optional, "looks fine" | Tests with every change; findings tagged `[BLOCKER] … [NIT]`; round limits |
| You find out at the end | Checkpoints you choose (spec, plan, release); everything is in files you can read |
| Hard to repeat | The same team, in any tool, any session, any teammate |

**What the evidence says so far.** In one controlled run of the same spec, a single agent's first pass failed 7 of 55 outside checks and the starter team's first pass 9, with the unreviewed builds' own tests green. A critical second pass fixed most of it in both arms (team 53/55; solo with a self-review pass 54/55), so a second look matters, but this run does **not** show that the second look must come from a different agent. Details, caveats and what would make it conclusive: [`evals/receipt-tally`](evals/receipt-tally/README.md). Every review finding from the worked examples is logged in `findings.csv` next to each example.

## Who it's for

- **New to software** — founders, product people, analysts, designers, operators. Describe what you want (or point at documents you wrote). The team picks the right agents, makes and records the technical choices, explains everything in plain language, and asks only for decisions that are yours.
- **Software professionals** — engineers, tech leads, platform teams building the AI-native way. Pick roles à la carte or define your own team, set your conventions, models and strictness, override or write roles, and wire it into your repo, CI and PR flow. Or just use it as is.

Same engine and quality bar for both — independent review, tests with every change, **a human holding the merge** — with different dials (`experience: beginner … expert`).

## Quick start

Prerequisites: `git` and **Python 3.8+** (the CLI is one standard-library file; nothing to install) and an AI tool.

Pick the entry that matches where you are:

| I have… | Do this |
|---|---|
| **Only an idea** | Open your AI tool in an empty folder and paste the [bootstrap prompt](docs/bootstrap-prompt.md). The Team Builder interviews you, recommends a lean or full team, installs it, and explains how to start. |
| **A product concept / technical plan in a repo**, and I use the **Claude app** | Add a small `CLAUDE.md` pointer, start a Code session on the repo, say *"Kick off this project with autocraft."* → [Kick off from your own documents](docs/kickoff-existing-docs.md) |
| **An existing codebase**, and I'm an **engineer** | `python3 autocraft/bin/autocraft init . --tool claude-code --team starter --add-role architect,qa-engineer --experience expert` → [For software engineers](docs/user-guide/6-for-software-engineers.md) |
| **A terminal** and a project in mind | the commands below |

```bash
git clone https://github.com/sak-io/autocraft.git
python3 autocraft/bin/autocraft recommend "an app where my students book yoga classes on their phone and pay online"
python3 autocraft/bin/autocraft init ~/code/yoga --tool claude-code --team mobile --archetype mobile-app,api-service
cd ~/code/yoga && claude          # then type:  /start
```

## How it works

```
        what you build                 who builds it                     where it runs
   ┌─────────────────────┐      ┌──────────────────────┐        ┌───────────────────────────┐
   │ 20 archetypes       │      │ 22 roles → 10 teams  │        │ Claude Code (CLI/web/app) │
   │ 10 capabilities     │ ───► │ + 13 workflows       │ ─────► │ Claude app (chat Projects)│
   │ (api, mobile, web,  │      │ (lean → full)        │ export │ Cursor · GitHub Copilot   │
   │  AI, data, game, …) │      │ customizable         │        │ Gemini CLI · Windsurf     │
   └─────────────────────┘      └──────────────────────┘        │ Cline · Codex & AGENTS.md │
                                                                 │ any chat (plain prompts)  │
                                                                 └───────────────────────────┘
```

| Ingredient | What it is | Where |
|---|---|---|
| **Roles** (22) | Job descriptions for agents: requirements-analyst, architect, principal-engineer, ux-designer, developer (and backend/frontend/mobile/data/ML/AI/DevOps/embedded/game variants), pr-reviewer, qa-engineer, security-auditor, release-gatekeeper, technical-writer, delivery-lead, repo-onboarder, team-builder | [`roles/`](roles/) |
| **Teams** (10) | A roster plus a playbook for a kind of software, from the lean `starter` to full teams | [`teams/`](teams/) |
| **Workflows** (15) | Procedures you start with a command: `/discover`, `/kickoff`, `/start`, `/design-architecture`, `/build-feature`, `/lean-build` (low-token, tool-agnostic task board; [guide](docs/lean-orchestration.md)), `/review-pr`, `/review-guide` (a reviewer's guide for big diffs, [guide](docs/reviewing-large-prs.md)), `/release-check`, `/security-scan`, `/status`, `/explain`, … They switch on automatically when their roles are present. | [`workflows/`](workflows/) |
| **Archetypes** (20) | Software-type profiles (API, web app, mobile app, AI assistant, data pipeline, game, infrastructure, …): the questions to ask, what the architecture must cover, how to test, what to scan, what to check before release. Includes a recipes table ("online store", "SaaS", "Slack bot"). | [`archetypes/`](archetypes/README.md) |
| **Capabilities** (10) | Cross-cutting needs with safe defaults and must-test lists: authentication, payments, database, email, uploads, search, observability, secrets, hosting, privacy | [`capabilities/`](capabilities/README.md) |
| **Protocol** | The contract between roles: handoff blocks, severity-tagged reviews, round limits, human gates, git modes, `gh` vs GitHub tools | [`docs/protocol.md`](docs/protocol.md) |
| **CLI** | One stdlib-only Python file that exports the above into each tool's native format | [`bin/autocraft`](bin/autocraft) |

Roles don't share a mind — they share **files**: specs, architecture and ADRs, work breakdown, handoffs and reviews (`.autocraft/work/<task>/`), `docs/STATUS.md`, plus PR labels when GitHub is used. That is what makes the team portable across tools, sessions and people.

### What a run looks like

```
idea / your documents → spec → plan (architect ⇄ principal) → build (parallel developers ⇄ reviewers)
        ▲ you answer       ▲ you approve                                  │
                                                  QA · security audit ◄───┘ → release check → you merge
```
Agents stop for you at the gates you set (`autonomy_level` 1–3), when they disagree for more than `max_review_rounds`, and for decisions only you can make (money, legal, accounts). They never merge to `main`.

## Supported AI tools

| Tool | What you get | Status | Guide |
|---|---|---|---|
| **Claude Code** (terminal, desktop, web, Claude app code sessions) | 1 subagent per role, workflows as `/commands`, `CLAUDE.md`, safe-command allowlist | **Exercised end to end** (see examples) | [claude-code](docs/tools/claude-code.md) |
| **Claude app** (chat Projects) | Project instructions + knowledge files; one model plays the roles | Generated; chat can't run code | [claude-app](docs/tools/claude-app.md) |
| **Cursor** | `.cursor/rules/*.mdc` | Format per vendor docs, not run in product | [cursor](docs/tools/cursor.md) |
| **GitHub Copilot** | `.github/agents/*.agent.md`, prompt files, instructions | same | [copilot](docs/tools/copilot.md) |
| **Gemini CLI** | `GEMINI.md` + `.gemini/commands/*.toml` | same | [gemini-cli](docs/tools/gemini-cli.md) |
| **Windsurf** | `.windsurf/rules/*.md` | same | [windsurf](docs/tools/windsurf.md) |
| **Cline** | `.clinerules/` | same | [cline](docs/tools/cline.md) |
| **Codex, Jules, Aider, Zed, … ** | `AGENTS.md` + `.autocraft/roles/` | same | [agents-md](docs/tools/agents-md.md) |
| **Any chat** | pasteable `prompts/` | — | [prompts](docs/tools/prompts.md) |

Tools without real sub-agents run the team as **role hats**, with a fresh session for every reviewer ([orchestration patterns](docs/orchestration-patterns.md)). Vendor formats change; each exporter is a small function in `bin/autocraft`.

## Pick a team

Start **lean**, grow when you've seen a reason. Every team keeps *a builder who isn't the judge of their own work*, *a security check*, and *a human who merges*.

| Team | For | Core roles |
|---|---|---|
| [**starter**](teams/starter.md) (lean) | anything small; start here when unsure | requirements-analyst · developer · pr-reviewer · security-auditor |
| [**web-product**](teams/web-product.md) | websites, web apps, SaaS, internal tools | + ux-designer · architect · principal-engineer · frontend/backend developers · qa · release-gatekeeper · delivery-lead |
| [**api-backend**](teams/api-backend.md) | APIs, jobs, queues, realtime, automation | architect · principal · backend-developer · qa · reviewer · security · release gate |
| [**mobile**](teams/mobile.md) | iOS/Android (+ backend) | ux-designer · mobile-developer · backend-developer · device-aware qa · store-aware release gate |
| [**ai-product**](teams/ai-product.md) | chatbots, assistants, RAG, agents | ai-engineer · eval-first qa · injection red-team |
| [**data-ml**](teams/data-ml.md) | pipelines, analytics, ML | data-engineer · ml-engineer · data-quality qa |
| [**platform**](teams/platform.md) | cloud infrastructure as code | devops-engineer · plan-first review |
| [**toolsmith**](teams/toolsmith.md) | libraries, CLIs, plugins, desktop | semver & compatibility gates · technical-writer |
| [**makers**](teams/makers.md) | games, embedded/IoT | game/embedded developer · playtest & OTA gates |
| [**setup**](teams/setup.md) | (meta) builds your team | team-builder |

Combine them: `--team mobile,ai-product`. Or define your own (`.autocraft/custom/teams/<id>.md`).

## Customize

Everything is files you own. Edit config and `custom/`, never generated files; `sync` regenerates, `doctor` flags drift.

```bash
autocraft add-role qa-engineer                      # add a specialist
autocraft remove-role ux-designer                   # drop one
autocraft new-role compliance-reviewer              # invent your own, then add-role it
autocraft add-tool cursor                           # same team, another AI tool
autocraft init . --role-model pr-reviewer=sonnet    # per-role model (Claude Code)
echo "Use pnpm and TypeScript strict." > .autocraft/custom/team-rules.md          # rules for every role
echo "- Prefer Vitest." > .autocraft/custom/roles/developer.append.md              # rules for one role
autocraft sync && autocraft doctor
```

Levels, from light to heavy: config knobs → team rules → per-role rules → replace a role → new role → custom workflow → your own team → fork. See [customizing](docs/customizing.md) and [for software engineers](docs/user-guide/6-for-software-engineers.md).

### CLI reference

| Command | Does |
|---|---|
| `autocraft list roles\|teams\|workflows\|archetypes\|capabilities\|tools` | browse the catalog |
| `autocraft recommend "<idea>" [--file doc.md …]` | first-guess archetypes, capabilities, teams and design-risk flags (keyword heuristic) |
| `autocraft init [DIR] --tool … --team … [--archetype … --capability … --add-role … --remove-role … --sources … --git-mode … --experience … --autonomy … --owner … --role-model … --lang …]` | install the team into a project |
| `autocraft sync [DIR]` | regenerate all tool files from `.autocraft/config.yml` + `custom/` |
| `autocraft add-role\|remove-role <id>` · `add-tool\|remove-tool <id>` · `new-role <id>` | edit the roster and tools |
| `autocraft pointer [DIR] --sources …` | write the `CLAUDE.md` pointer for a documents-first kickoff |
| `autocraft github [DIR] --lang …` | add CI, security scanning and GitHub templates |
| `autocraft doctor [DIR]` | check config, manifest, drift, sources, the `.gitattributes` generated-file block |
| `autocraft init\|sync … --commit` | commit the autocraft-owned files as ONE dedicated commit (`init --no-gitattributes` opts out of the generated-file markers) |
| `autocraft review-map [DIR] [--base REF] [--head REF] [--json] [--slices] [--emit-split-script] [--verify-guide FILE]` | what is in this diff (product / tests / docs / config / generated), whether a reviewer's guide is recommended, a stacked-PR split proposal, and a check that every `path:line` in a guide still exists; deterministic, no model tokens ([details](docs/reviewing-large-prs.md)) |

## Repository layout

```
roles/  teams/  workflows/        the tool-neutral core (markdown with frontmatter)
archetypes/  capabilities/        domain profiles roles read as requirements
bin/autocraft                     the CLI and all tool exporters (stdlib Python)
templates/                        architecture & release templates, CI for 8 stacks, branch protection, kickoff pointer
scripts/                          validate.sh (checks everything), onboard-repo.sh (optional GitHub hardening)
docs/                             user guide, per-tool pages, protocol, lifecycle, bootstrap prompt, glossary
examples/                         worked examples (below)
.claude/  .autocraft/  CLAUDE.md  this repo using its own setup team, so opening it in Claude Code starts a /build-my-team
```

## Documentation

| For | Read |
|---|---|
| Everyone | [**User Guide**](docs/user-guide/README.md) — what it is, getting started, a first project, day to day, choosing/customizing a team, FAQ, feedback form |
| New to software | [Beginner guide](docs/vibe-coders.md) · [Glossary](docs/glossary.md) |
| Engineers | [For software engineers](docs/user-guide/6-for-software-engineers.md) · [Protocol](docs/protocol.md) · [Orchestration patterns](docs/orchestration-patterns.md) · [Customizing](docs/customizing.md) |
| Claude app users | [Kick off from your own documents](docs/kickoff-existing-docs.md) · [Claude app](docs/tools/claude-app.md) · [Bootstrap prompt](docs/bootstrap-prompt.md) |
| Big pull requests | [Reviewing large PRs](docs/reviewing-large-prs.md) — generated-file markers, the separate install commit, `review-map`, the reviewer's guide, the split offer |
| Concepts | [Lifecycle](docs/lifecycle.md) · [Archetypes & recipes](archetypes/README.md) · [Capabilities](capabilities/README.md) |

## Examples

| Example | What it shows | Status |
|---|---|---|
| [**ClassBook**](examples/classbook/README.md) | A yoga-studio booking app built end to end with real, separate agents: spec → architecture (2 review rounds) → six tasks (three built in parallel) → QA → security audit. 26 agent runs, ≈2.2 M tokens (the last, lean-mode round took ≈190 k), 539 tests passing. Includes what went wrong. | Release-ready for merge; deployment (host sign-up) is the only open item |
| [**Receipt Tally**](examples/receipt-tally/README.md) | A small command-line tool (bank CSV to monthly spending summary) built with the lean 4-role team and a token budget set up front. 4 agent runs, ≈270 k tokens, 36 tests, independent review included. Shows what to skip and what not to. | Finished; a local tool, nothing to deploy |
| [**Pantry Pal kickoff**](examples/pantry-pal-kickoff/README.md) | The documents-first flow: a product concept + technical plan with planted contradictions → the team found all of them (22 gaps) | Rehearsal of the first steps |
| [Order API walkthrough](docs/example-order-service.md) | A conceptual, narrated walkthrough on an order-management API | Illustrative |

The owner in both examples is simulated; the agents' outputs are real.

## Status and honest limits

- **Only the Claude path has been exercised end to end.** The other exporters follow vendors' documented formats but haven't been run in those products.
- **A full run from the Claude app on a phone has not been done yet**; the documents-first kickoff was rehearsed in a cloud session, and the install, ingestion and spec steps worked.
- Agents make mistakes. The process (independent review, tests, CI, a human merge) is what catches them — don't remove the human gate for anything important. Multi-agent runs are token-hungry (ClassBook ≈ 2 M tokens) and can hit usage limits; work is saved at every step.
- Not supported yet: per-project custom archetypes/capabilities, per-directory teams in a monorepo.
- `recommend` is a keyword heuristic; the Team Builder agent reads your documents properly.

## Contributing and validation

Add a role, team, workflow, archetype, capability, language CI template or tool exporter by following the patterns in [customizing](docs/customizing.md#extend-the-framework-itself-contribute). `bash scripts/validate.sh` checks structure and cross-references, generates all nine tool exports into a temp project, verifies the YAML/TOML parse, exercises custom teams and per-role models, and confirms `sync` is idempotent; the same runs in CI on every pull request.

**License:** [Apache-2.0](LICENSE).
