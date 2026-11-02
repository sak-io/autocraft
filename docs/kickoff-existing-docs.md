# Kick off a project from your own documents (Claude app)

**For you if:** you have already written down what the product is and how it should be built (a product concept, a technical plan, notes — in markdown files in a GitHub repository) and you want Claude, from the **Claude app** (phone, web or desktop), to build it with a team of agents.

**What happens in one sentence:** you point a Claude *Code* session at your repository; it reads your documents, installs the right agent team (using autocraft), turns your documents into a reviewed spec and plan — flagging gaps and contradictions for you to decide — then builds, tests, reviews and security-checks the product with several agents working in parallel, and finally asks you to merge.

> **Status:** the pieces below are built and the install step has been exercised in a simulated session. A full run from the Claude app on your phone has not been done yet, so treat the first project as a pilot and tell us what to fix. Known rough edges are listed in [Troubleshooting](#troubleshooting).

---

## What you need (one time)

| Need | How |
|---|---|
| The **Claude app** with **Code** sessions | Claude app → *Code* tab |
| **GitHub connected** to Claude | Claude settings → connect GitHub (claude.ai/connect-github) and allow access to **your project repo**. (`sak-io/autocraft` is public, so no special access is needed to clone it.) |
| Your **project repo** with your documents | e.g. `docs/product-concept.md` and `docs/technical-plan.md` (any names; markdown) |

You do **not** need a terminal, Python on your phone, or any setup in the repo beyond one small file (next).

## Step 1 — Put your documents in the repo

Anything that explains the product. The more specific the better, but gaps are fine: the team is built to find them. Typical:

```
your-repo/
  docs/product-concept.md     what, for whom, why, features, business model, principles
  docs/technical-plan.md      stack, data, integrations, hosting, constraints
```

## Step 2 — Add the pointer (the "reference to autocraft")

Create a file named **`CLAUDE.md`** in the root of your repo containing the text below (on GitHub: *Add file → Create new file*; works from the GitHub mobile app). Claude Code sessions read `CLAUDE.md` automatically, so this is how the session learns what to do. Change the document names to yours.

```markdown
# This project is built with an autocraft agent team

**Owner's source documents (authoritative inputs):** `docs/product-concept.md`, `docs/technical-plan.md`
**Framework:** `sak-io/autocraft` on GitHub (a public repository; no special access is needed to clone it).

## Kickoff (the team is not installed in this repo yet)
When the owner asks you to kick off / start / build this project:

1. **Get autocraft into this session.** If `/tmp/autocraft` does not exist, clone it OUTSIDE this repo: `git clone https://github.com/sak-io/autocraft /tmp/autocraft`. If the clone is blocked by the session's network settings, make sure `sak-io/autocraft` is in scope (the owner may have selected it when starting the session; otherwise use the `add_repo` tool for it) and try again. If it still fails, or the clone has no `bin/autocraft`, tell the owner exactly which step failed and stop.
2. **Act as the `team-builder`.** Read `/tmp/autocraft/roles/team-builder.md` and `/tmp/autocraft/workflows/kickoff.md` and follow them (section "Pointer-driven kickoff"). Read the source documents yourself, run `python3 /tmp/autocraft/bin/autocraft recommend --file <each source document>` as a first guess only, explain the lean and full options in plain words (including contradictions or risks you noticed in the documents), recommend one, and ask the owner at most 4 short questions.
3. **Install after the owner confirms**, mapping the answers to flags: `python3 /tmp/autocraft/bin/autocraft init . --tool claude-code --sources docs/product-concept.md,docs/technical-plan.md --git-mode session-branch --team <team> --add-role <extra roles> --archetype <types> --capability <needs> --experience <beginner|intermediate|expert> --autonomy <1|2|3> --owner <owner's GitHub handle> --commit`. Notes: `--tool claude-code` is correct for Claude app Code sessions too. For a project that arrives with a technical plan, "lean" means `--team starter --add-role architect` (add `qa-engineer` when personal data or access control is involved). Do NOT pass `--lang` yet: CI and GitHub hardening are added later, after the plan is approved.
4. **The installation is its own commit, made before any product work.** `--commit` (step 3) creates ONE commit with only the autocraft-owned files (`chore(autocraft): install agent team (generated files)`); never mix them into product commits and never use `git add -A`. Those files are marked `linguist-generated` in `.gitattributes`, so GitHub collapses them in pull requests. Then `git push -u origin HEAD` (if there is no remote, skip). If the owner wants human review of a PR, the bootstrap commit can be opened as a small separate PR first, or filtered out of the review. Tell the owner in plain words what was added: the team (`.claude/agents`, commands in `.claude/skills`), a one-time copy of the framework in `.autocraft/framework` (so later sessions do not need to fetch autocraft again), and `.claude/settings.json` which pre-approves routine safe commands (git, tests, the autocraft tool).
5. **Continue with the `kickoff` workflow** (now installed in `.claude/skills/`): ingest the source documents into a spec, validate the technical plan, get the owner's approval, then build with reviewers, QA and a security check. This pointer is replaced by the full team guide as soon as `autocraft init` runs.

Never paste or commit secrets. Nothing reaches `main` until the owner merges the pull request.
```

(From a computer you can generate this exact file: `python3 autocraft/bin/autocraft pointer . --sources docs/product-concept.md,docs/technical-plan.md`.)

## Step 3 — Start the session and say one sentence

In the Claude app: **Code → New session → choose your project repository** (also add `sak-io/autocraft` if the app lets you pick more than one repo; if not, the pointer makes the session ask for it). Then type:

> **Kick off this project with autocraft.**

That is all. From here the session leads; you answer and approve.

## What you will see (and what you do)

| # | What the agents do | What you do | Typical time for you |
|---|---|---|---|
| 1 | **Team Builder** reads your documents, tells you in plain words what it understood, **points out contradictions and risks it already noticed in them**, and recommends a **lean** or **full** team. Asks ≤ 4 short questions (off-limits things, how often to be asked, notifications and your GitHub handle). | Answer; confirm the team. *Not sure? Take lean.* | 2–3 min |
| 2 | Installs the team into your repo and **commits it on its own** (one commit, `chore(autocraft): install agent team (generated files)`, before any product work): the agents (`.claude/agents`), the commands (`.claude/skills`), a **one-time copy of the framework** in `.autocraft/framework` (so later sessions don't need to fetch autocraft again), and `.claude/settings.json` that pre-approves routine safe commands. These files are marked as generated, so GitHub collapses them when you review a pull request; if you want to review closely, open that bootstrap commit as a small separate pull request first. It tells you this in plain words. | Nothing. | 0 |
| 3 | **Spec (`/kickoff` step 1):** the requirements analyst turns your concept into a spec with testable acceptance criteria, each citing the section of *your* document it came from, plus a numbered list of **gaps, ambiguities and contradictions** with a recommended default for each. | Answer the questions that matter (defaults are fine). Say "AGREED". | 5–10 min |
| 4 | **Plan (step 2):** the architect adopts *your* technical plan (your choices become decisions "given by owner"), checks it against the spec, flags risks, and writes the task list. A principal engineer challenges it, up to 3 rounds. | Read the plain-language summary. Approve — or say "keep it simpler". | 5–10 min |
| 5 | **Build (step 3):** a foundation task first, then independent tasks **in parallel** — each builder writes code **and tests**; a *different* reviewer runs the tests itself and probes. Findings go back and forth (max 3 rounds). | Nothing; skim the short per-task summaries. | seconds each |
| 6 | **QA and security (step 4):** an independent tester (authorization matrix, race conditions, accessibility, exploratory) and a security auditor (dependency scan, code scan, secrets, threat model). Defects become failing tests, then get fixed. | Read the two plain-language summaries; decide anything marked "your decision". | 5 min |
| 7 | **Release check (step 5):** last look for what review can't see (settings, migrations, rollback, docs). | Read "what ships / risk / how to undo it". | 3 min |
| 8 | The session branch is ready. | **You open the pull request and merge** (or ask: "open the pull request"). | 3 min |

The team **never merges to `main` and never opens a pull request unless you ask.** Work is committed and pushed to the session's branch as it goes, so if the session ends, nothing is lost.

## Stopping, resuming, and steering

- **Resume in a new session** (same repo): type `/status`. The state is in `docs/STATUS.md` and the commits, not in chat memory.
- **Ask for less:** *"Stop after the plan and wait for me."* · *"Use only the lean team."* · *"Keep it as simple as safely possible."*
- **Change your mind:** edit your documents (or say it in chat). The requirements analyst updates the spec and tells you which tasks change.
- **Session ended or paused?** Work is saved at every step (files and commits). Continue in a new session with `/status`.
- **Fewer approval taps on a phone:** the install adds `.claude/settings.json` that pre-approves routine, safe commands (git, running tests, the autocraft tool). Review it once.

## What it costs

Independent roles each carry their own context, so a team uses more tokens than one agent doing everything; that is the price of separation and review. The [ClassBook example](../examples/classbook/README.md) — a small app — used 26 agent runs and ≈2.2 million tokens, mostly in review and QA (its last round, run with `token_mode: lean`, took ≈190 thousand), for about 30–40 minutes of the owner's attention. Your project's size decides yours. Start lean (`--token-saver`); add QA and security when the product is real.

## Troubleshooting

| Problem | What to do |
|---|---|
| The session doesn't mention autocraft | `CLAUDE.md` isn't at the repo root or wasn't committed to the branch you selected. Check it, or just paste the pointer text into the chat. |
| Cloning `sak-io/autocraft` fails | It is a public repo, so this is normally the session's network settings. Start the session with `sak-io/autocraft` also selected (or let the session use the `add_repo` tool), or paste the pointer text and say *"use the add_repo tool for sak-io/autocraft"*. |
| The clone has no `bin/autocraft` | You cloned a stale fork or the wrong branch. Use `https://github.com/sak-io/autocraft` (branch `main`). |
| It says it can't use `gh` | Normal in cloud sessions. The team uses the session's GitHub tools instead (protocol §13). |
| A new agent role "isn't available" | The role files were created this session. The team lead falls back to a general-purpose agent that reads the role file. If it doesn't, say: *"use a general-purpose agent and have it read .claude/agents/<role>.md"*. |
| It starts building before you approved the plan | Say *"Stop. Wait for my approval at each gate."* and set `autonomy_level: 1` in `.autocraft/config.yml`. |
| The plan feels too heavy for your idea | Say *"This is v1; keep the design as simple as safely possible."* |
| You pushed new documents but the team ignores them | Mention them: *"Re-read docs/…; update the spec and tell me what changed."* |

See also: [Claude app tool page](tools/claude-app.md) · [User Guide](user-guide/README.md) · [Protocol](protocol.md)
