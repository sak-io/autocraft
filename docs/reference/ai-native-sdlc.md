# The AI-native SDLC and autocraft

Anthropic's [AI-native SDLC playbook](https://claude.com/resources/articles/the-ai-native-sdlc-playbook) argues that code is no longer the bottleneck, so the controls around it (planning, review, testing, deploy) must work as a loop of committed artifacts with humans at the gates. That matches autocraft's design. This page maps the playbook to autocraft, and says what is **tool-neutral** (works in every supported tool because it is plain files and written rules) and what is **tool-specific enforcement** (a bonus where your tool supports it).

## The principle
*The agent may act up to a gate and cannot pass it.* Each stage commits an artifact the next stage reads; the commit history is the audit trail ([protocol section 17](../protocol.md)).

## Mapping

| Playbook practice | In autocraft | Neutral or tool-specific |
|---|---|---|
| Capture intent once (`intent.md`) | `templates/intent/intent.md`; `requirements-analyst` consumes it and must answer its open questions | Neutral (files) |
| Requirements and design as one reviewed spec | `docs/specs/`, `requirements-analyst`, spec gate at `autonomy_level` 1 | Neutral |
| Plan mode: `plan.md` before code | `developer` writes `.autocraft/work/<task>/plan.md` (`templates/plan/plan.md`); reviewer compares diff to plan | Neutral (a rule plus a file); tools with a read-only plan mode can use it for the same step |
| Feedback loop: tests, build, lint are part of done; fix code not tests; failing test first for bug fixes | Protocol section 17; `developer` role | Neutral rule. A hook that blocks test-file edits during fix tasks is possible only where the tool has hooks |
| CLAUDE.md: day-one essentials, "mistake twice goes in" | `.autocraft/custom/team-rules.md`, exported by `sync` to every tool's instruction file | Neutral |
| Skills as institutional knowledge | Capabilities, archetypes and `team-rules.md`; workflows export as each tool's skills or commands | Neutral source, native export |
| Hooks as deterministic guardrails and approval gates | Protocol "production is a human gate" rule. Claude Code gets a generated `PreToolUse` hook and `deny` rules; Cursor and Gemini CLI get a shell hook running the same gate script, which logs each decision with a timestamp | Rule is neutral; enforcement is generated for **Claude Code, Cursor and Gemini CLI** |
| Parallel sessions in worktrees; start with 2 or 3 | `max_parallel_developers`, protocol section 8 and 14 | Neutral |
| Verifier subagent | `qa-engineer` and the independent `pr-reviewer`, which re-run the tests themselves | Neutral |
| AI in the PR loop, `REVIEW.md`, severity ranking, author cannot approve own code | `pr-reviewer`, severity tags, `templates/review/REVIEW.md`, separation of duties | Neutral |
| Code owner approval, branch protection | `scripts/onboard-repo.sh`, `templates/branch-protection.json` | GitHub-enforced, any AI tool |
| CI/CD: read-only first, writes only as PRs, production gated, rehearsed rollback | `release-gatekeeper`, CI templates, `deployment-hosting` capability, release checklist | Neutral |
| Continuous evals when agent config changes | `templates/evals/` (task format, `run_evals.py` that works with any agent CLI) and an opt-in `agent-evals.yml`; each incident adds an eval ([protocol section 17](../protocol.md)) | Neutral; you supply the agent command and API key |
| Maintain: detect, diagnose, write findings back as intent | Operate phase, `security-auditor`; `templates/operate/bands.yaml` (deterministic detection, tiered response) and `templates/intent/incident-intent.md` (an anomaly becomes an intent plus an eval) | Neutral; detection is your monitoring |
| Scheduled security scans | `/security-scan`, weekly gitleaks and dependency scan, CodeQL, Dependabot | CI-enforced, tool-agnostic |
| Metrics (first-pass merge rate, rework cycles, time intent to merge) | `autocraft metrics` reads git history; `autocraft doctor` lints handoffs, `plan.md` and intent files | Neutral |

## Adopting it, in the playbook's order
The playbook's Figure 3 (the play dependency graph) says: start with any **entry point**, which needs nothing first; for any other play, adopt the plays that point into it first. In autocraft terms:

| Play | autocraft piece | Adopt after |
|---|---|---|
| Capture intent *(entry)* | `intent.md` template | nothing |
| Project instructions *(entry)* | `.autocraft/custom/team-rules.md` (exported as `CLAUDE.md`, `AGENTS.md`, ...) | nothing |
| Plan before code *(entry)* | `plan.md` | nothing |
| Feedback loop *(entry)* | build, test, lint commands that decide "done" (protocol section 17) | nothing |
| Hooks and gates *(entry)* | production gate, deny rules, branch protection | nothing |
| Requirements and design | spec from `intent.md` | intent; policy skills help |
| Skills | capabilities, archetypes, policies in `team-rules.md` | project instructions |
| Subagents | roles (`qa-engineer` as verifier) | project instructions; feedback loop helps |
| Evals | regression tasks run in CI (not built yet) | project instructions, feedback loop |
| PR review | `pr-reviewer` with `REVIEW.md` | evals, project instructions; skills help |
| CI/CD | CI templates, `release-gatekeeper` | PR review, hooks |
| Closing the loop | an anomaly becomes a new intent | intent, PR review, CI/CD, hooks |

So: begin with the five entry points, build the human gates (hooks, branch protection) before automating anything that passes through them, and add review and CI/CD only once the plays pointing into them exist.

## Enforcement per tool
Instructed rules reach every tool through `sync`. Mechanical enforcement depends on the tool. GitHub branch protection and CI work with any tool. On top of that, `init` writes guardrail files once, only in formats the tool's official docs describe, and never overwrites them afterwards:

| Tool | Production gate and irreversible commands | Secrets | Page |
|---|---|---|---|
| Claude Code | `.claude/settings.json` `PreToolUse` hook; `deny` rules | `Read` deny rules | [claude-code](tools/claude-code.md) |
| Cursor | `.cursor/hooks.json` `beforeShellExecution` hook (fail-closed) | `.cursor/cli.json` deny (Cursor CLI only); `.cursorignore` | [cursor](tools/cursor.md) |
| Gemini CLI | `.gemini/settings.json` `BeforeTool` hook; `tools.exclude` | none documented at project level | [gemini-cli](tools/gemini-cli.md) |
| Copilot, Windsurf, Cline, AGENTS.md, plain prompts | none generated; the protocol rule applies | none | [tools](tools/) |

All three hooks run the same script, `production-gate.py`, which blocks production deploys until a human sets `RELEASE_APPROVAL`, and blocks force-push, push to `main`/`master` and `rm -rf`. Policy lives in the protocol; each tool's file is just one way to enforce it. Hooks are a floor, not a sandbox: a determined agent can route around string matching, so branch protection stays the real backstop.

## Measuring it
The playbook pairs every play with a leading and a lagging indicator. What autocraft can read today:

- **Intent**: time from the first intent to the spec commit, and how often the intent is edited after the spec exists (`autocraft metrics`).
- **Design**: spec commits after the first `plan.md`, which is requirements rework (`autocraft metrics`).
- **Build**: branch commits and time to merge per merge commit; a one-commit branch is the proxy for a first-pass merge (`autocraft metrics`; squash merges are invisible to it).
- **Rules file**: corrections to `team-rules.md` (`autocraft metrics`); the same mistake appearing in review twice is the signal to add one.
- **Gates**: blocked and approved gate decisions (`.autocraft/gate.log`, shown by `autocraft metrics`).
- **Test, review, CI/CD, maintain**: first-pass CI rate, review time, DORA measures and incident-to-eval time come from your CI, PR history and incident tracker; autocraft does not collect them.

## What the playbook assumes that autocraft does not generate
The playbook's examples are Claude Code features. The neutral rule is in the protocol; where a tool has the feature, configure it by hand, and CI or branch protection cover the rest.

| Playbook feature | Neutral position |
|---|---|
| Managed (admin-owned) settings that engineers cannot override | Not generated. Use your tool's organization-level settings if it has them. Without them, a hook in the repo is a floor that a developer can edit, so branch protection and CODEOWNERS on the hook files are the backstop |
| OS-level sandbox, network allowlist, credential file and environment deny | Not generated. Run agent jobs in a container with scoped, short-lived tokens and no standing production credentials (protocol section 17) |
| Deployment exposed as MCP tools scoped per environment | Not generated. The protocol's tiered autonomy applies to any mechanism; the generated gate stops production deploys until a human authorizes them |
| Managed code review service, `@claude` fix loop, Claude Tag on call | Tool-specific. `pr-reviewer` and `REVIEW.md` give the same review passes in any tool; the severity tally line lets CI read the counts |

## Not yet (candidate next steps)
- **Guardrail files for Copilot, Windsurf and Cline**, once their docs describe a project-level permission or hook format.
- **Edit-time hooks** that block edits to protected paths and to test files during fix tasks. They need a documented file-edit hook in each tool; today the protocol rule and the reviewer enforce it.
- **Eval content**: the runner and format exist, but the 20 to 50 tasks have to come from your own work.
