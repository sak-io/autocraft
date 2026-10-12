<!-- autocraft:begin (managed block - edit .autocraft/custom/, then run autocraft sync) -->
# Agent team (managed by autocraft)

This project is built by a **team of role-specialised AI agents** working with a human owner. Teams: **Starter Team (lean)**.
Software type: fullstack-app - Capabilities: secrets-and-config, deployment-hosting, analytics-observability, authentication, database, email-and-notifications - Audience level: beginner.

## Roles
| Role | What it does | How to invoke |
|---|---|---|
| `requirements-analyst` | Turns a rough product idea into a clear, testable spec (goals, user stories, acceptance criteria, non-goals, open questions). | subagent `requirements-analyst` |
| `developer` | Implements one work item from the approved work breakdown on a feature branch, with unit and integration tests, and opens a pull… | subagent `developer` |
| `pr-reviewer` | Reviews pull requests for correctness, tests, security, design fit and maintainability; posts structured feedback; re-reviews aft… | subagent `pr-reviewer` |
| `security-auditor` | Runs and triages SCA (dependency) and SAST (code) scans, secret scans and threat-model checks on a schedule or on demand; files p… | subagent `security-auditor` |
| `architect` | Designs the system architecture for a service or product from a spec - components, data model, APIs, security, deployment, testin… | subagent `architect` |
| `principal-engineer` | Senior reviewer who critiques and approves (or rejects) architecture, ADRs, threat models and work breakdowns produced by the arc… | subagent `principal-engineer` |
| `qa-engineer` | Independent quality engineer: derives a test plan from acceptance criteria, writes and maintains automated tests (unit gaps, inte… | subagent `qa-engineer` |
| `release-gatekeeper` | Final pre-release check on an already-approved PR - looks only for remaining gaps (docs, migrations, config, security, rollback,… | subagent `release-gatekeeper` |

## Workflows
- `/discover` - Turns a plain-language idea ("I want an app where…") into a recommended set of archetypes and capabilities, explained in simple w…
- `/explain` - Explains any file, PR, review comment, error, agent decision or technical term in plain language for a non-engineer, with what it…
- `/start` - Guided beginner-friendly kickoff for a new software project.
- `/build-feature` - Implements a work item end to end - developer writes code plus unit and integration tests and opens a PR, then pr-reviewer and de…
- `/review-pr` - Reviews a single pull request (new or updated) with the pr-reviewer agent.
- `/security-scan` - Runs the security-auditor to collect and triage SCA, SAST and secret-scan results, write an audit report, and file prioritized is…
- `/status` - Shows where the project is in the lifecycle, what is in flight, what is blocked and what the human needs to do next, in plain lan…
- `/design-architecture` - Runs the architect and principal-engineer in a review loop until the architecture is approved (max 3 rounds, then escalate to the…
- `/release-check` - Final pre-release gate on an approved PR.

## How to run the team in this tool
Roles run as separate agents with their own context. A role cannot call another role; the main session coordinates the loops (author -> reviewer -> author) and enforces the round limit.

# Playbook: Starter Team

**Idea → Spec → Build → Review → You merge.**

1. `requirements-analyst` writes a short spec with acceptance criteria (half a page for small things).
2. `developer` builds one small task at a time on a branch, with tests.
3. `pr-reviewer` reviews in a **fresh context** — never the same session that wrote the code — and the two iterate (max 3 rounds, then ask you).
4. `security-auditor` runs before you ship anything real, and weekly after.
5. You review the summary and merge.

**Why this works:** even this tiny team gets the biggest benefit of multi-agent work — a builder who is not the judge of their own work. Grow into a bigger team when the project grows (`autocraft init . --team web-product`).

## Non-negotiable rules
1. Never commit to `main`; all changes go through a pull request (or a reviewed branch). **Never merge - humans merge.**
2. Every behavior change ships with unit tests, and integration tests when it crosses a boundary (database, network, queue).
3. Never commit secrets. Never disable or skip a test, check or protection to get green.
4. `docs/architecture/` is the source of truth; declare any deviation in the PR.
5. Review feedback uses severity tags `[BLOCKER] [MAJOR] [MINOR] [NIT] [QUESTION]`; blockers and majors must be resolved before approval.
6. After the configured number of review rounds, stop and ask the human (`needs-human`).
7. Hand off with the block in `.autocraft/protocol.md`; keep `docs/STATUS.md` current. State lives in the repo, not in chat memory.

## Where things live
Specs `docs/specs/` - architecture `docs/architecture/` (+`status.md`) - decisions `docs/adr/` - design `docs/design/` - status `docs/STATUS.md` -
config `.autocraft/config.yml` - archetypes `.autocraft/archetypes/` - capabilities `.autocraft/capabilities/` - protocol `.autocraft/protocol.md` -
customizations `.autocraft/custom/` (edit these, then `autocraft sync`).
<!-- autocraft:end -->
