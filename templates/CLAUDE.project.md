# Project guide for the agent team

This project is built by a team of specialised Claude agents working with a human owner. **Read this file first.**

## The team (`.claude/agents/`)
| Agent | Job |
|---|---|
| `requirements-analyst` | Idea → spec with testable acceptance criteria |
| `architect` | Spec → architecture, API, threat model, ADRs, work breakdown |
| `principal-engineer` | Reviews/approves architecture (loops with architect) |
| `repo-onboarder` | Repo, CI, lint/test, SCA/SAST, branch protection — verified |
| `developer` | One task → one PR with unit + integration tests; fixes review feedback |
| `pr-reviewer` | Reviews every PR and every update; approves when clean |
| `release-gatekeeper` | Final gap check on approved PRs; marks release-ready |
| `security-auditor` | Triage of SCA/SAST/secret findings |
| `delivery-lead` | Tracks state, enforces limits and human gates |

## Workflows (`/skills`)
`/start` · `/design-architecture` · `/onboard-repo` · `/build-feature` · `/review-pr` · `/release-check` · `/security-scan` · `/status`

## Non-negotiable rules
1. Never commit to `main`; all changes via PR. Never merge — **humans merge**.
2. Every behavior change ships with unit tests, and integration tests when crossing a boundary.
3. Never commit secrets. Never disable or skip a test, check, or protection to get green.
4. Architecture is the source of truth (`docs/architecture/`); deviations must be declared in the PR.
5. Review feedback uses severity prefixes: `[BLOCKER] [MAJOR] [MINOR] [NIT] [QUESTION]`. Blockers/majors must be resolved before approval.
6. Max review rounds and parallelism are in `.autocraft/config.yml`; hitting the limit means label `needs-human`.
7. Hand off with the block defined in `docs/protocol.md`; keep `docs/STATUS.md` current.

## State lives in the repo, not in memory
Specs `docs/specs/` · Architecture `docs/architecture/` (+`status.md`) · Decisions `docs/adr/` · Status `docs/STATUS.md` · PR labels `agent:*` · Config `.autocraft/config.yml`.

## Commands
<!-- onboarding fills these in -->
- Install: 
- Lint: 
- Unit tests: 
- Integration tests: 
- Build: 
