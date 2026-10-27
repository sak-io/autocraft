# Claude app (web, iOS, Android, desktop)

The Claude app gives you **two different ways** to work with autocraft. Pick by what you need:

| You want | Use | Real parallel agents? | Runs code and tests? |
|---|---|---|---|
| Real software built, tested, reviewed — from a repository | **Code session** (the *Code* tab) | **Yes** | Yes, in a cloud container |
| To think, plan, write specs, review designs — no repo | **Chat Project** | No (one model plays the roles) | No |

## A. Code session (recommended): the full team, from your phone or browser

A Code session is Claude Code running in the cloud against your GitHub repository. Everything autocraft does in a terminal works here, including **sub-agents running in parallel**.

**Start from documents you already wrote** → [Kick off a project from your own documents](../kickoff-existing-docs.md). (One small `CLAUDE.md` pointer in your repo, then one sentence in the app.)

**Start from only an idea** → use the [bootstrap prompt](../bootstrap-prompt.md) in a Code session attached to an empty repo.

What is different from a terminal, and how autocraft handles it:

| Cloud session reality | How autocraft adapts |
|---|---|
| No `gh` command; GitHub *tools* instead | Roles use `gh` if present, otherwise the tools (protocol §13) |
| The session is given one branch and may not push other branches or open PRs unprompted | `git_mode: session-branch` (default): work and commit on the session branch; parallel tasks use local worktrees; handoffs/reviews are files; a PR only when you ask |
| Sub-agent files created during the session | Spawn them by role id; if one isn't registered yet, the team lead uses a general-purpose agent that reads the role file |
| Many approval taps on a phone | `.claude/settings.json` pre-approves routine safe commands (git, tests, autocraft) |
| Sessions end | State lives in files (`docs/STATUS.md`, `.autocraft/work/`) and commits; `/status` resumes in a new session |
| Token budget | Start lean (`--token-saver`); QA and security are the biggest costs; work is saved at each step |

You are asked at the **gates** (spec, plan, anything only you can decide) and for the **final merge**. The team never merges to `main`.

## B. Chat Project (no repo, no code execution)

Good for discovery, specs, architecture reviews, and learning.

```bash
python3 autocraft/bin/autocraft init ~/code/my-idea --tool claude-app --team starter
```
Writes `claude-project/INSTRUCTIONS.md` and `claude-project/knowledge/*.md`. Create a Project in claude.ai, paste the instructions, upload the knowledge files, and say "Let's start." Don't have a computer? Paste the chat prompt from the [bootstrap prompt](../bootstrap-prompt.md).

**Independence trick:** open a *new chat in the same Project* for each reviewer role and paste only the spec and the work to review.

A chat can't run code or tests; for implementation switch to a Code session with the same team (your specs carry over as files).
