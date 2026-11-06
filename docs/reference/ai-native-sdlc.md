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
| Hooks as deterministic guardrails and approval gates | Protocol "production is a human gate" rule. Claude Code also gets a generated `PreToolUse` hook (`.claude/hooks/production-gate.py`) and `deny` rules | Rule is neutral; **enforcement is Claude Code only** today |
| Parallel sessions in worktrees; start with 2 or 3 | `max_parallel_developers`, protocol section 8 and 14 | Neutral |
| Verifier subagent | `qa-engineer` and the independent `pr-reviewer`, which re-run the tests themselves | Neutral |
| AI in the PR loop, `REVIEW.md`, severity ranking, author cannot approve own code | `pr-reviewer`, severity tags, `templates/review/REVIEW.md`, separation of duties | Neutral |
| Code owner approval, branch protection | `scripts/onboard-repo.sh`, `templates/branch-protection.json` | GitHub-enforced, any AI tool |
| CI/CD: read-only first, writes only as PRs, production gated, rehearsed rollback | `release-gatekeeper`, CI templates, `deployment-hosting` capability, release checklist | Neutral |
| Continuous evals when agent config changes | Not built yet. See "Not yet" | Would be CI-based and tool-agnostic |
| Maintain: detect, diagnose, write findings back as intent | Operate phase, `security-auditor`; an anomaly becomes an intent file | Neutral; detection is your monitoring |
| Scheduled security scans | `/security-scan`, weekly gitleaks and dependency scan, CodeQL, Dependabot | CI-enforced, tool-agnostic |
| Metrics (first-pass merge rate, rework cycles, time intent to merge) | Derivable from git history and `agent-runs.csv` | Neutral |

## Adopting it, in the playbook's order
1. Start with the no-prerequisite plays: write an intent file, put your build/test/lint commands and recurring mistakes in `team-rules.md`, ask for `plan.md` before code.
2. Build the human gates before more automation: turn on branch protection (`scripts/onboard-repo.sh`), keep `autonomy_level` at 1 or 2.
3. Add `REVIEW.md` for your repository and tune it monthly (rate findings, cap nits).
4. Raise parallelism only while review keeps up.

## Enforcement per tool
Instructed rules reach every tool through `sync`. Mechanical enforcement depends on the tool: GitHub branch protection and CI work with any tool; the generated permission deny list and production-gate hook are Claude Code only. For another tool, check its page under [tools](tools/) for an equivalent (permissions file, hooks, rules), and apply the same policy there. Policy lives in the protocol; each tool's file is just one way to enforce it.

## Not yet (candidate next steps)
- **Continuous evals**: collect 20 to 50 real tasks with acceptance checks and run them in CI when `team-rules.md`, roles or hooks change.
- **A metrics command** computing the playbook's indicators from git history.
- **Equivalent guardrail files for other tools** where they support permissions or hooks.
- A handoff lint in `doctor` for `plan.md` and handoff fields.
