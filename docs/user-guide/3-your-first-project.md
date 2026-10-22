# 3. Your first project, step by step

> *Written step by step for people new to software. If you're a software professional, skim the gates and step 5, then read [page 6](6-for-software-engineers.md) — same journey, with the dials exposed.*

This page walks the whole journey once. For a complete real run with every output, see the [ClassBook worked example](../../examples/classbook/README.md).

**The journey in one picture**

```
 1 Describe  →  2 Choose team  →  3 Spec  →  4 Plan  →  5 Build + review  →  6 Release check  →  7 You merge
   (you)          (you+agent)     (agent)    (agents)    (agents, loops)       (agent)            (you)
                                      ▲ you answer questions   ▲ you approve the plan          ▲ you approve
```

Throughout, you can type **`/status`** (where are we?) and **`/explain <anything>`** (say it simply).

---

## Step 1 — Describe your idea (2 minutes)

Type `/discover` (or just tell the Team Builder). Describe it like you'd tell a smart friend: who it's for and what they should be able to do. Don't worry about technology.

> *"I run a small yoga studio. Students should be able to see our classes, book a spot, and cancel. Classes have limited spots. I want to add classes myself. Payments can come later."*

**What the agent does:** maps your words to a *software type* (here: a web app with accounts and a database), lists what it will probably need (login, database, email), and tells you what it suggests **leaving out of version 1**.

**What you do:** confirm, correct, or add. *"Actually, no accounts needed — students just enter their email"* is a perfectly good answer.

## Step 2 — Choose your team (2 minutes)

The Team Builder offers two options in plain words:

- **Lean** — a planner, a builder, an independent reviewer, and a security checker. Fast, low ceremony.
- **Fuller** — adds an architect and a principal engineer who debate the design, a QA specialist, a release checker, and so on.

**Our advice:** if you're unsure, take **lean** and add roles later (`autocraft add-role architect`). Choose fuller up front if there's money, personal data, or other people's safety involved.

**What you do:** pick one. It installs the team into your project and tells you how to start.

## Step 3 — The spec (5 minutes of your time)

`/start` begins. The **requirements-analyst** writes `docs/specs/<name>.md`: goals, the people who use it, user stories, *acceptance criteria* ("given/when/then" checks that can be tested), things explicitly **out of scope**, and numbered open questions.

**What you do:** answer the questions. Every question has a suggested default, so *"use the defaults"* is valid. Read the **Out of scope** list — it's where you protect yourself from the project ballooning.

> **Gate:** you confirm the spec. Everything downstream is built from it.

## Step 4 — The plan (5 minutes of your time)

With a fuller team, the **architect** designs and the **principal engineer** challenges it. They go back and forth up to 3 rounds, in files you can read (`docs/architecture/`). You get a plain-language summary: what will be built, the main choices and why, the biggest risks, and the list of small tasks.

With the lean team, the builder writes a half-page plan instead.

**What you do:** read the summary, ask `/explain` about anything unclear, approve. If two agents genuinely disagree after 3 rounds they stop and ask you, with both positions laid out and a recommendation.

> **Gate:** you approve the plan. (At autonomy level 3 you can skip this gate; not recommended at first.)

## Step 5 — Build and review (agents work; you glance)

`/build-feature` takes the next small task. For each task:

1. **Builder** writes the code **and tests** on its own branch.
2. **Reviewer** (a different agent, fresh context) reviews and writes findings tagged by severity:

   | Tag | Plain meaning | Blocks approval? |
   |---|---|---|
   | `[BLOCKER]` | wrong or unsafe | yes |
   | `[MAJOR]` | important gap (e.g. missing tests) | yes |
   | `[MINOR]` | should fix | no, if tracked |
   | `[NIT]` | taste | no |
   | `[QUESTION]` | reviewer needs an answer | until answered |

3. **Builder** answers every comment — fixes it, or explains why not — and the reviewer re-checks each point. Repeat up to 3 rounds.
4. When there are **no open blockers or majors** and the checks pass, the reviewer approves.

Independent tasks can run **in parallel** with several builders.

**What you do:** nothing required. After each task you get a 3-line summary: what was built, the test evidence, and how many review rounds it took. Skim it. If something worries you, `/explain`.

## Step 6 — Release check

`/release-check` (with a `release-gatekeeper`) looks only for what review doesn't: leftover debug code, settings and secrets, database changes that could break a live system, missing documentation, a rollback plan. Gaps go back to the builder. When clean, the change is marked **release-ready** and you're told, with:

- **What ships** (one sentence), **risk** (low/medium/high and why), **how to undo it**.

## Step 7 — You merge

Open the change, read the summary and the checklist, confirm the automated checks are green, and approve/merge it. That click is the one thing agents will never do for you.

---

## What to expect (from the worked example)

The [ClassBook example](../../examples/classbook/README.md) — a booking app for a yoga studio, built with the lean team plus four added roles — recorded what a small real project costs:

| | ClassBook |
|---|---|
| Agent runs | 26 (several in parallel) |
| Tokens used | ≈ 2.2 million (the independent QA pass alone was ≈ 320 thousand; the final fix-and-review round, in lean mode, ≈ 190 thousand) |
| Agent time | ≈ 104 minutes in total (less on the clock: builders and reviewers ran in parallel) |
| Your effort (estimated) | ≈ 30–40 minutes, in short moments |
| Review rounds | architecture 2; tasks: 5 of 6 approved first time, 1 needed a fix round |
| What reviewers caught that builders missed | a design that broke "sign in, then return to the class"; a lock-out that would have hit the owner; a test that couldn't fail; a crash on huge IDs; and two correct branches that only broke when merged |

**Two lessons from it:**
1. **Say "simpler" at the plan gate.** The architect built a more careful design than a one-room studio needs. The reviewer judged it sound, not proportionate. If the plan looks heavier than your idea deserves, tell the team: *"This is a small studio, keep it as simple as safely possible."* It will redo the plan.
2. **Budget for the big steps.** Independent QA and security checks are the most valuable *and* the most expensive steps. Long runs can reach your AI tool's usage limit; work is saved in your files (`/status` resumes it), but plan for pauses. Starting with the lean team keeps usage down.

## Your time, realistically

| Step | Your effort |
|---|---|
| Describe + choose team | a few minutes |
| Spec questions | 5–10 minutes |
| Approve the plan | 5–10 minutes |
| Per task | seconds to a couple of minutes (skim the summary) |
| Release | a few minutes per release-ready change |

**Next:** [4. Day to day →](4-day-to-day.md)
