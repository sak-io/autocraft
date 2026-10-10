# autocraft

**A team of AI agents for the whole software lifecycle** — architecture, review, repo setup, building, code review, pre-release checks and security — packaged as ready-to-use [Claude Code](https://claude.com/claude-code) agents and skills.

You bring the idea. The agents behave like a disciplined engineering team: they design, challenge each other, build with tests, review each other's work, and hand you a *release-ready* pull request. **You stay in control: humans approve and merge.**

> New to software engineering? Start with **[docs/getting-started.md](docs/getting-started.md)**. No prior knowledge assumed.

## The team

```
 idea
  │
  ▼
requirements-analyst ──► architect ⇄ principal-engineer      (design loop, max 3 rounds)
                                │ approved
                                ▼
                         repo-onboarder        (private repo, protected main, CI, lint, tests, SCA/SAST)
                                │
                                ▼
              developer(s) ⇄ pr-reviewer       (build loop per PR: code + unit/integration tests)
                                │ approved
                                ▼
                       release-gatekeeper      (final gap check → label release-ready)
                                │
                                ▼
                       👤 you review & merge

        security-auditor   (weekly + pre-release: triage SCA/SAST/secret findings)
        delivery-lead      (tracks state, enforces limits, tells you what's next)
```

| Agent | One-line job |
|---|---|
| [requirements-analyst](.claude/agents/requirements-analyst.md) | Vague idea → testable spec |
| [architect](.claude/agents/architect.md) | Spec → architecture, API, threat model, ADRs, task list |
| [principal-engineer](.claude/agents/principal-engineer.md) | Critiques and approves the architecture |
| [repo-onboarder](.claude/agents/repo-onboarder.md) | Creates & hardens the GitHub repo, verifies every control |
| [developer](.claude/agents/developer.md) | One task → one PR with unit + integration tests |
| [pr-reviewer](.claude/agents/pr-reviewer.md) | Reviews each PR and every update until clean |
| [release-gatekeeper](.claude/agents/release-gatekeeper.md) | Last look at approved PRs; marks **release-ready** |
| [security-auditor](.claude/agents/security-auditor.md) | Triage of dependency / code / secret scan results |
| [delivery-lead](.claude/agents/delivery-lead.md) | Status board, next action, human gates |

## Workflows (slash commands)

| Command | What it does |
|---|---|
| `/start` | Guided kickoff for a new project — runs everything below in order |
| `/design-architecture` | architect ⇄ principal-engineer loop until approved |
| `/onboard-repo` | Create + harden the GitHub repo |
| `/build-feature` | developer ⇄ pr-reviewer loop (parallel tasks supported) |
| `/review-pr <n>` | Review any single PR |
| `/release-check` | Pre-release gate → `release-ready` → notify you |
| `/security-scan` | SCA / SAST / secrets triage |
| `/status` | Where are we, what's next, what do you need to do |

## Quick start

```bash
# 1. Get the framework
git clone https://github.com/sak-io/autocraft.git && cd autocraft

# 2. Install it into a new (or existing) project folder
bash scripts/install.sh ~/code/my-service --lang node     # node | python | go

# 3. Open Claude Code there and kick off
cd ~/code/my-service && claude
> /start
```

Prerequisites: [Claude Code](https://claude.com/claude-code), `git`, the [GitHub CLI](https://cli.github.com) (`gh auth login`), and `jq`.

## How agents collaborate

Agents don't talk in secret: everything they exchange lives **in the repo** (docs, PR comments, labels), so you can read it, and any session can pick up where the last left off. Full rules: **[docs/protocol.md](docs/protocol.md)**. Highlights:

- **Review loops** use severity-tagged feedback (`[BLOCKER] [MAJOR] [MINOR] [NIT]`), must-answer comments, and a **3-round limit** before escalating to you.
- **PR labels are the state machine:** `agent:needs-review → agent:changes-requested ⇄ agent:approved → agent:release-ready`.
- **You choose how involved to be** (autonomy levels L1–L3).

## Learn more

| Doc | For |
|---|---|
| [Getting started](docs/getting-started.md) | First-timers: setup → first project |
| [Lifecycle](docs/lifecycle.md) | Each phase: inputs, outputs, quality gates |
| [Protocol](docs/protocol.md) | Handoffs, labels, review rules, autonomy levels |
| [Worked example](docs/example-order-service.md) | An e-commerce order API, start to release |
| [Customizing](docs/customizing.md) | Add agents, change stacks, tune strictness |
| [Glossary](docs/glossary.md) | Plain-language definitions of the jargon |

## Repository layout

```
.claude/agents/      the agent definitions (copied into your projects)
.claude/skills/      the slash-command workflows
templates/           CI workflows, PR/issue templates, architecture & release templates, branch protection
scripts/             install.sh, onboard-repo.sh, validate.sh
docs/                guides and protocol
```

Validate the framework itself: `bash scripts/validate.sh`.

## Honest limitations

- Agents make mistakes; the process (tests, CI, independent review, human merge) is what catches them. Don't remove the human gate for anything important.
- Some GitHub protections need a paid plan for private repos; the onboarder reports what it could and could not enable.
- Claude Code subagents can't spawn other subagents, so the *skills* run the loops from the main session.
