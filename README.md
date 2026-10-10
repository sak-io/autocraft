# autocraft

**Agent teams for building software with AI — pick your kind of software, pick your AI tool, get a ready-made team.**

Most people build software with *one* AI agent doing everything: planning, coding, and judging its own work. It works until it doesn't — mistakes go unnoticed, context gets muddled, and nobody is holding the quality bar. Professional teams solve this with **roles**: someone who defines the problem, someone who designs, someone who builds, someone *else* who reviews, someone who checks before release.

autocraft gives you that team as plain files your AI tool already understands — and a small CLI (plus an agent, the **Team Builder**) that sets it up for you, in the tool you use, for the kind of software you're building, and lets you customize it.

> **Never set up agents before?** Don't read further — open your AI tool in an empty folder and paste the **[bootstrap prompt](docs/bootstrap-prompt.md)**. The Team Builder interviews you and does the rest.

## How it works

```
        what you build                 who builds it                     where it runs
   ┌─────────────────────┐      ┌──────────────────────┐        ┌───────────────────────────┐
   │ 20 archetypes       │      │ 22 roles → 10 teams  │        │ Claude Code (CLI/web/app) │
   │ 10 capabilities     │ ───► │ + workflows          │ ─────► │ Claude app (chat Projects)│
   │ (api, mobile, web,  │      │ (lean → full)        │ export │ Cursor · GitHub Copilot   │
   │  AI, data, game, …) │      │ customizable         │        │ Gemini CLI · Windsurf     │
   └─────────────────────┘      └──────────────────────┘        │ Cline · Codex & AGENTS.md │
                                                                 │ any chat (plain prompts)  │
                                                                 └───────────────────────────┘
```

One tool-neutral definition → exported into each tool's **native** format (subagents, rules, custom agents, commands, instructions). Learn once, switch tools freely, keep your team.

## 60-second start

```bash
git clone https://github.com/sak-io/autocraft.git
python3 autocraft/bin/autocraft recommend "an app where my students book yoga classes on their phone and pay online"
python3 autocraft/bin/autocraft init ~/code/yoga --tool claude-code --team mobile --archetype mobile-app,api-service
cd ~/code/yoga && claude        # then type:  /start
```

Or let an agent do it: [`docs/bootstrap-prompt.md`](docs/bootstrap-prompt.md). Only Python 3.8+ is needed (no installs).

## Your AI tool

| Tool | What you get | Guide |
|---|---|---|
| **Claude Code** (terminal, desktop, web, Claude app code sessions) | 1 subagent per role in `.claude/agents/`, workflows as `/slash` skills, `CLAUDE.md` | [claude-code](docs/tools/claude-code.md) |
| **Claude app** (chat Projects, mobile) | Project instructions + knowledge files; the model plays the team in one chat | [claude-app](docs/tools/claude-app.md) |
| **Cursor** | `.cursor/rules/*.mdc` — role & workflow rules | [cursor](docs/tools/cursor.md) |
| **GitHub Copilot** | `.github/agents/*.agent.md`, prompt files, `copilot-instructions.md` | [copilot](docs/tools/copilot.md) |
| **Gemini CLI** | `GEMINI.md` + `.gemini/commands/*.toml` | [gemini-cli](docs/tools/gemini-cli.md) |
| **Windsurf** | `.windsurf/rules/*.md` | [windsurf](docs/tools/windsurf.md) |
| **Cline** | `.clinerules/` | [cline](docs/tools/cline.md) |
| **Codex, Jules, Aider, Zed, … (AGENTS.md)** | `AGENTS.md` + `.autocraft/roles/` | [agents-md](docs/tools/agents-md.md) |
| **Anything else** (ChatGPT, …) | pasteable `prompts/` | [prompts](docs/tools/prompts.md) |

Tools without real sub-agents run the team as **role hats** with a fresh session for every reviewer — see [orchestration patterns](docs/orchestration-patterns.md). Vendor file formats change; each exporter is a small function in [`bin/autocraft`](bin/autocraft).

## Pick a team

Start **lean**, grow when needed. Every team keeps the three things that matter: *a builder who isn't the judge of their own work*, *a security check*, and *a human who merges*.

| Team | For | Roles (core) |
|---|---|---|
| **[starter](teams/starter.md)** (lean) | anything small; start here when unsure | requirements-analyst · developer · pr-reviewer · security-auditor |
| **[web-product](teams/web-product.md)** | websites, web apps, SaaS, internal tools | + ux-designer · architect · principal-engineer · frontend/backend-developer · qa · release-gatekeeper · delivery-lead |
| **[api-backend](teams/api-backend.md)** | APIs, jobs, queues, realtime, automation | architect · principal · backend-developer · qa · reviewer · security · release gate |
| **[mobile](teams/mobile.md)** | iOS/Android (+ backend) | ux-designer · mobile-developer · backend-developer · qa (device matrix) · release gate (store-aware) |
| **[ai-product](teams/ai-product.md)** | chatbots, assistants, RAG, agents | ai-engineer · eval-first QA · injection red-team |
| **[data-ml](teams/data-ml.md)** | pipelines, analytics, ML models | data-engineer · ml-engineer · data-quality QA |
| **[platform](teams/platform.md)** | cloud/infrastructure as code | devops-engineer · plan-first review |
| **[toolsmith](teams/toolsmith.md)** | libraries, CLIs, plugins, desktop | semver & compatibility gates · technical-writer |
| **[makers](teams/makers.md)** | games, embedded/IoT | game-developer / embedded-engineer · playtest & OTA gates |
| **[setup](teams/setup.md)** | (meta) builds your team | team-builder |

Teams combine: `--team mobile,ai-product`. Browse the [22 roles](roles/), the [20 software-type archetypes](archetypes/README.md) (with a recipes table: "online store", "SaaS", "Slack bot", …) and [10 capabilities](capabilities/README.md) (login, payments, database, email, uploads, search, privacy, …).

## Customize it

Everything is files you own; generated files are never the place to edit.

```bash
autocraft add-role qa-engineer            # add a specialist
autocraft remove-role ux-designer         # drop one
autocraft new-role compliance-reviewer    # invent your own, then add-role it
autocraft add-tool cursor                 # support another AI tool, same team
echo "Use pnpm and TypeScript strict." > .autocraft/custom/team-rules.md   # rules for every role
echo "- Prefer Vitest." > .autocraft/custom/roles/developer.append.md      # rules for one role
autocraft sync                            # regenerate every tool's files
autocraft doctor                          # sanity-check the setup
```
Details: [docs/customizing.md](docs/customizing.md). Strictness knobs (autonomy level, review rounds, parallel builders, audience level `beginner|intermediate|expert`) are in `.autocraft/config.yml`.

## The collaboration model (the same in every tool)

Roles don't share a mind — they share **files**: specs, reviews, handoff blocks and a status file, plus PR labels when GitHub is used. That is what makes the team portable across tools and sessions. Authors answer every review comment; reviewers re-verify each one; after N rounds they stop and ask you; **humans merge**. Full rules: [docs/protocol.md](docs/protocol.md). The lifecycle: [docs/lifecycle.md](docs/lifecycle.md).

## Optional: GitHub hardening module
If your project lives on GitHub, `autocraft github --lang python` (or [`scripts/onboard-repo.sh`](scripts/onboard-repo.sh)) adds CI, linting/test steps, SCA/SAST/secret scanning, labels, templates and branch protection for `main`, and the `repo-onboarder` role verifies each control. It is a module, not the point — the team works without it.

## Learn more
[Beginner guide](docs/vibe-coders.md) · [Why teams & orchestration patterns](docs/orchestration-patterns.md) · [Bootstrap prompt](docs/bootstrap-prompt.md) · [Lifecycle](docs/lifecycle.md) · [Protocol](docs/protocol.md) · [Worked example](docs/example-order-service.md) · [Glossary](docs/glossary.md)

## Honest limitations
- Agents make mistakes; the process (tests, independent review, CI, human merge) is what catches them. Don't remove the human gate for anything important.
- Non-Claude exports follow each vendor's documented conventions as of writing; formats evolve, so run `autocraft doctor` and check the vendor docs if a tool ignores the files.
- Chat-only tools can't run tests; for real repo work use an agentic tool (Claude Code, Cursor, Copilot, Gemini CLI, …).

Validate the framework itself: `bash scripts/validate.sh`.
