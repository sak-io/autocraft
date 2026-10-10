# autocraft User Guide

> **Review draft v0.1** — written to be read and criticised. If anything is confusing, too long, too short, or untrue when you try it, that is exactly the feedback we need. See [Give feedback](7-give-feedback.md).

**Who this is for:** people who are technical in spirit — analysts, product managers, designers, operators, founders, power users — but who are **not professional software developers**, and who want to build software with AI agents without having to learn how software teams work.

**What autocraft does in one sentence:** it gives you a small *team* of AI agents (planner, builder, reviewer, security checker, …) instead of one agent doing everything, set up for the *kind* of thing you want to build, with you approving the decisions that matter.

## Read in this order

| # | Page | Time | You will learn |
|---|---|---|---|
| 1 | [The idea: why a team of agents](1-the-idea.md) | 5 min | The mental model. What you do vs. what the agents do. |
| 2 | [Getting started](2-getting-started.md) | 10 min | Set up in your tool — terminal, Claude app (phone/web), or other tools. |
| 3 | [Your first project, step by step](3-your-first-project.md) | 15 min | The full journey from idea to something you can merge. |
| 4 | [Day to day](4-day-to-day.md) | 10 min | Commands, reading reviews, changing your mind, resuming work. |
| 5 | [Choosing and customizing your team](5-choosing-your-team.md) | 10 min | Lean vs full, software types, add/remove roles, your own rules. |
| 6 | [FAQ and troubleshooting](6-faq-and-troubleshooting.md) | as needed | "It's stuck", "I don't understand", "is it safe?" |
| 7 | [Give feedback](7-give-feedback.md) | 20 min | A short test script + questions. |

**See it in action:** [the ClassBook worked example](../../examples/classbook/README.md) — a real app built end-to-end by following this guide, with every step and every agent output.

## How much to trust this guide (honest status)

| Area | Status |
|---|---|
| Team roles, teams, workflows, software-type profiles | Written and structurally validated |
| Setup CLI and exports for 9 tools (Claude Code, Claude app, Cursor, Copilot, Gemini CLI, Windsurf, Cline, AGENTS.md, plain prompts) | Generated files verified well-formed. **Only the Claude path has been exercised end-to-end** (see the worked example). The others follow each vendor's documented format but have not been run in the vendor's product. |
| Claude app (Code sessions on web/phone) | Works for the team itself. **Known gaps are listed in each page's "Today's limits" box** — for example, pull-request steps rely on the session's GitHub tools. |
| Time and cost figures | Taken from the worked example only; your project will differ |

Anything marked **Today's limits** is a known rough edge, not a mystery.

## Vocabulary used throughout

- **Agent / role** — an AI with one job description (e.g. *reviewer*).
- **Team** — the set of roles chosen for your kind of software.
- **Workflow** — a repeatable procedure you start with a slash command, like `/start`.
- **Human gate** — a point where agents stop and wait for you.
- **Spec** — the written description of what to build. **Architecture** — the plan of how.
- More in the [glossary](../glossary.md).
