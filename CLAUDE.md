<!-- autocraft:begin (managed block - edit .autocraft/custom/, then run autocraft sync) -->
# Agent team (managed by autocraft)

This project is built by a **team of role-specialised AI agents** working with a human owner. Teams: **Setup Team (meta)**.
Software type: (not chosen yet - run `discover`) - Capabilities: secrets-and-config, deployment-hosting, analytics-observability - Audience level: beginner.

## Roles
| Role | What it does | How to invoke |
|---|---|---|
| `team-builder` | Interviews the human about what they want to build and which AI tool they use, recommends the right agent team (and a lean or ful… | subagent `team-builder` |

## Workflows
- `/build-my-team` - Sets up the right team of AI agents for the software you want to build, in the format of the AI tool you use (Claude Code, Claude…
- `/customize-team` - Changes an installed agent team - add or remove roles, switch teams, tune strictness, add house rules and standards, create a bra…
- `/discover` - Turns a plain-language idea ("I want an app where…") into a recommended set of archetypes and capabilities, explained in simple w…
- `/explain` - Explains any file, PR, review comment, error, agent decision or technical term in plain language for a non-engineer, with what it…

## How to run the team in this tool
Roles run as separate agents with their own context. A role cannot call another role; the main session coordinates the loops (author -> reviewer -> author) and enforces the round limit.

# Playbook: Setup Team

Used on its own, before any project team exists. `team-builder` interviews you (idea → software type → AI tool → experience), recommends a lean and a full team, installs them with `autocraft init`, explains how to use them in your tool, and later changes them with `autocraft sync`. Everything it does is plain files you can read.

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
