# The lifecycle

These phases are the same in every tool. A *team* decides which roles are present (the lean `starter` team collapses several phases into builder + reviewer); an *archetype* decides what each gate checks.

| # | Phase | Agents | Inputs | Outputs | Exit gate |
|---|---|---|---|---|---|
| 0 | Discover & kickoff | `/discover`, `/start` | your idea in plain words | `.autocraft/config.yml` (archetypes, capabilities, experience, autonomy) | you confirmed the plan |
| 1 | Spec | requirements-analyst | idea | `docs/specs/*.md` | every story has testable acceptance criteria; open questions answered or assumed |
| 1b | UX design (UI archetypes only) | ux-designer | spec | `docs/design/` flows, wireframes, states, accessibility | every story maps to screens and states |
| 2 | Architecture | architect ⇄ principal-engineer | spec | architecture, API, threat model, ADRs, work breakdown | `status.md = APPROVED`, 0 open BLOCKER/MAJOR |
| 3 | Onboarding | repo-onboarder | approved architecture | repo, CI, scanning, protection, `docs/onboarding-report.md` | no ❌; every control read back |
| 4 | Build | developer(s) ⇄ pr-reviewer | a ready task | PR with unit + integration tests | `VERDICT: APPROVED`, CI green |
| 5 | Pre-release | release-gatekeeper (+developer) | approved PR | `agent:release-ready` + human notified | checklist all ✅/N-A |
| 6 | Release | **human** | release-ready PR | merged to `main`, deployed | human approval |
| 7 | Operate | security-auditor, delivery-lead | repo | audits, issues, status | ongoing |

## Quality gates in detail

**Architecture gate** – traceable to requirements, simplest design that works, threat model is real, testing strategy concrete, tasks small and ordered.
**Repository gate** – `main` protected (PR + review + status check `ci`, no force-push), CI runs lint + unit + integration + build + dependency audit, CodeQL + Dependabot + secret scanning on, labels/templates present.
**PR gate** – acceptance criteria met, unit *and* integration tests that really assert behavior, secure by default, matches architecture, CI green on latest commit, all comments answered.
**Release gate** – migrations safe, config documented, rollback plan, observability, docs/changelog, no leftover debug code, security scans clean.

## Feedback loops
```
architect ──draft──► principal-engineer
          ◄─findings─┘   (≤3 rounds → human)

developer ──PR──────► pr-reviewer
          ◄─comments─┘   (≤3 rounds → human)

developer ──approved PR─► release-gatekeeper
          ◄─[RELEASE-BLOCKER]─┘ (≤3 rounds → human)
```

## Typical timeline for a small service
Spec (minutes) → Architecture (2-3 rounds) → Onboarding (minutes, needs your confirmation) → T1 walking skeleton → T2…Tn features, each a PR → release check on each.

## The lifecycle adapts to the archetype
The phases are the same for every project; the *content* of the gates changes. See [archetypes](../archetypes/README.md): e.g. mobile adds store review + staged rollout to the release gate, jobs add idempotency and missed-run alerting, web adds accessibility and E2E journeys, libraries add semver and public-API stability, APIs add contract compatibility and authorization checks.
