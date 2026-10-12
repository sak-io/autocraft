# 1. The idea: why a team of agents

## The problem with "one agent does everything"

Most people start by asking a single AI assistant to plan, build, test, and judge its own work. It feels fast, and it often works for small things. It breaks down in predictable ways:

- **It marks its own homework.** The agent that wrote the code is the worst reviewer of that code.
- **Its memory gets muddled.** Planning, code, and error messages pile up in one long conversation until instructions get lost.
- **Nobody holds the quality bar.** Tests, security checks, and "is this really what was asked for?" are skipped when everything is moving fast.
- **You can't see what happened.** There are no checkpoints, so you either trust everything or read everything.

Professional software teams solved this decades ago with **roles and checkpoints** — code review, QA, security review, release gates. autocraft gives you the same structure, as AI agents you can staff, swap and tune.

## What you get

```
          YOU (decide, approve, merge)
            │
   ┌────────┴─────────────────────────────────────────┐
   │  planner → designer → builder(s) → reviewer →    │   a small team of agents,
   │            security check → release check         │   each with one job
   └───────────────────────────────────────────────────┘
        works in your AI tool (Claude, Cursor, Copilot, …)
        leaves everything in plain files you can read
```

| Without a team | With autocraft |
|---|---|
| One long chat | Separate agents, each with a clean, focused job |
| The builder reviews itself | A *different* agent reviews, in a fresh context |
| "Looks fine to me" | Written findings with severities: must-fix vs. nice-to-have |
| You find out at the end | You approve at checkpoints you choose |
| Tests optional | Tests required with every change |

## Who uses it, and how differently

| If you're… | You mostly… |
|---|---|
| **new to software** | describe what you want, answer a few plain-language questions, read short summaries, and click merge. The team makes and records the technical choices. |
| **a software professional** | choose which roles you want (or write your own), set your conventions and models, point the team at your repo and specs, and review the artifacts like you'd review a team's work. See [page 6](6-for-software-engineers.md). |

Same engine, same quality bar; different dials.

## The four ingredients

1. **Roles** — job descriptions for agents. There are 22 (planner, architect, reviewer, mobile developer, security auditor, …).
2. **Teams** — a sensible set of roles for a kind of software. Start with the **lean `starter` team** (4 roles); grow into bigger ones.
3. **Workflows** — procedures you trigger, such as `/start` (begin a project), `/build-feature`, `/release-check`, `/status`.
4. **Profiles** — knowledge about *your type of software* (website, mobile app, API, AI chatbot, scheduled job, game…) and common needs (login, payments, email…), so the agents ask the right questions and check the right things.

## What the agents do — and what you do

| Agents do | You do |
|---|---|
| Turn your idea into a written spec | Say what you want, in your own words; answer a few questions |
| Design the solution and argue about it (architect ⇄ principal engineer) | Read a plain-language summary; approve or redirect |
| Write the code **and the tests** | Nothing — unless they ask you something |
| Review each other's work and fix findings | Nothing — unless they get stuck after 3 rounds |
| Check security and release-readiness | Read the "release-ready" summary |
| — | **Merge.** Agents never merge or release on their own. |

## Three guarantees, whatever tool you use

1. **Independent review.** The agent that reviews never wrote the code.
2. **Tests with every change.** No test, no approval.
3. **A human merges.** You keep the last word.

## What this is not

- Not a magic "build my startup" button. You still decide *what* is worth building.
- Not a replacement for experts in regulated areas (health, finance, children's data, safety-critical devices). The agents will flag these and tell you to involve a professional.
- Not guaranteed bug-free. The process reduces and surfaces mistakes; it can't remove them.

**Next:** [2. Getting started →](2-getting-started.md)
