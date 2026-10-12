# autocraft User Guide

> **Review draft v0.2** — written to be read and criticised. If anything is confusing, too long, too short, or untrue when you try it, that is exactly the feedback we need. See [Give feedback](8-give-feedback.md).

## What autocraft is

Building software with *one* AI agent doing everything — planning, coding, and judging its own work — works until it doesn't: mistakes go unnoticed, context gets muddled, nobody holds the quality bar. autocraft gives you a **team of AI agents** instead — planner, designer, builders, independent reviewer, QA, security checker, release gate — chosen for the *kind* of software you're building, working in your AI tool (Claude first; Cursor, Copilot, Gemini CLI and others too), leaving everything in plain files you can read, with **you approving the decisions that matter and always holding the merge**.

## Who this is for

autocraft serves two audiences with the same engine. Pick the one that sounds like you — you can switch any time.

| | **New to software** | **Software professional** |
|---|---|---|
| Who | Founders, product managers, analysts, designers, operators, power users with an idea or a spec but without a software-engineering background | Engineers, tech leads, architects, platform teams who already build software and want to do it the AI-native way |
| What you want | An outcome — a working, tested product — without having to learn how software teams work | Leverage and control — a repeatable multi-agent workflow you can shape to your standards |
| How autocraft helps | Picks the right team for your kind of software, explains everything in plain language, makes the technical choices and records them, asks you only for decisions that are yours | Gives you a roster of specialised, swappable roles; lets you pick à la carte, override or write your own, set your rules, models and strictness, and wire it into your repo, CI and PR flow |
| Your dial | `experience: beginner` (default) — plain words, recommended defaults, few questions | `experience: expert` — terse, trade-offs, only genuine decisions |
| Start with | the **lean `starter` team** | whatever you'd hire for the job: **pick roles, or define your own team** |
| Your first pages | 1 → 2 → 3 → 4 | 1 (skim) → 2 → **6** → 5 |

Neither audience gets a different quality bar. **Independent review, tests with every change, no secrets in code, and a human holding the merge** apply to everyone; the first-time user just gets more explanation and the engineer gets more knobs.

## Read in this order

| # | Page | Time | You will learn |
|---|---|---|---|
| 1 | [The idea: why a team of agents](1-the-idea.md) | 5 min | The mental model. What you do vs. what the agents do. |
| 2 | [Getting started](2-getting-started.md) | 10 min | Set up in your tool — terminal, Claude app (phone/web), or other tools. |
| 3 | [Your first project, step by step](3-your-first-project.md) | 15 min | The full journey from idea to something you can merge. *(Newcomers: read it all. Engineers: skim.)* |
| 4 | [Day to day](4-day-to-day.md) | 10 min | Commands, reading reviews, changing your mind, resuming work. |
| 5 | [Choosing and customizing your team](5-choosing-your-team.md) | 10 min | Lean vs full, software types, add/remove roles, your own rules. |
| 6 | [**For software engineers**](6-for-software-engineers.md) | 10 min | Pick and choose roles, custom teams, per-role models, overrides, existing repos, CI drift checks, extending the framework. |
| 7 | [FAQ and troubleshooting](7-faq-and-troubleshooting.md) | as needed | "It's stuck", "I don't understand", "is it safe?", "can I turn that off?" |
| 8 | [Give feedback](8-give-feedback.md) | 20 min | A short test script + questions, with a track for each audience. |

**Already have your product concept / technical plan written down?** [Kick off a project from your own documents](../kickoff-existing-docs.md) (Claude app or terminal).

**See it in action:** [the ClassBook worked example](../../examples/classbook/README.md) — a real app built by following this guide, with every step and every agent output. (Status: release candidate; the final hardening round is pending — the example says exactly what is done and what is not.)

## How much to trust this guide (honest status)

| Area | Status |
|---|---|
| Team roles, teams, workflows, software-type profiles | Written and structurally validated |
| Setup CLI and exports for 9 tools (Claude Code, Claude app, Cursor, Copilot, Gemini CLI, Windsurf, Cline, AGENTS.md, plain prompts) | Generated files verified well-formed. **Only the Claude path has been exercised end-to-end** (see the worked example). The others follow each vendor's documented format but have not been run in the vendor's product. |
| Claude app (Code sessions on web/phone) | Works for the team itself; the documents-first kickoff has been rehearsed in a cloud session. **A full run from the phone app has not been done yet.** Known gaps are in each page's "Today's limits" box. |
| Customization (roles, teams, rules, per-role models) | Implemented and covered by the framework's validation |
| Time and cost figures | Taken from the worked example only; your project will differ |

Anything marked **Today's limits** is a known rough edge, not a mystery.

## Vocabulary used throughout

- **Agent / role** — an AI with one job description (e.g. *reviewer*).
- **Team** — the set of roles chosen for your kind of software.
- **Workflow** — a repeatable procedure you start with a slash command, like `/start` or `/kickoff`.
- **Human gate** — a point where agents stop and wait for you.
- **Spec** — the written description of what to build. **Architecture** — the plan of how.
- More in the [glossary](../glossary.md).
