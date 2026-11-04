# 2. Getting started

Pick the path that matches how you work. If you're unsure, take **Path B (Claude app)** if you use Claude on your phone or browser, or **Path A (terminal)** if you're comfortable opening a terminal.

| Path | You use | Real parallel agents? | Runs code and tests? |
|---|---|---|---|
| **A. Claude Code in a terminal / desktop** | `claude` on your computer | Yes | Yes (your machine) |
| **B. Claude app — Code session** (web, iOS, Android, desktop) | A cloud session attached to your GitHub repo | Yes | Yes (cloud container) |
| **C. Claude app — chat Project** | A normal chat | No — one model plays all roles | No |
| **D. Other tools** (Cursor, Copilot, Gemini CLI, Windsurf, Cline, Codex…) | Your existing tool | Depends on the tool | Yes, if the tool does |

> **Rule of thumb:** to build something real with tests, use A, B, or D. Use C to think, plan, and review without any setup.

---

> **Software engineer in a hurry?** Skip to [page 6](6-for-software-engineers.md): `autocraft init . --tool claude-code --team starter --add-role architect,qa-engineer --experience expert` in your repo, commit, done.

## What every path needs (once)

- A **GitHub account** (free is fine) — except Path C.
- The `autocraft` repository: `https://github.com/sak-io/autocraft` (public; clone it, nothing else to request).
- For terminal use: **Python 3.8+** and **git** (`python3 --version`, `git --version` should both print a version). Nothing else to install.

---

## Path A — Claude Code in a terminal

1. **Make a folder for your project** and open a terminal in it:
   ```bash
   mkdir ~/code/my-project && cd ~/code/my-project
   ```
2. **Get autocraft** (anywhere outside your project):
   ```bash
   git clone https://github.com/sak-io/autocraft.git ~/autocraft
   ```
3. **Ask for a recommendation** (optional — a quick first guess):
   ```bash
   python3 ~/autocraft/bin/autocraft recommend "an app where students book yoga classes and pay online"
   ```
4. **Install the team** (start lean if unsure):
   ```bash
   python3 ~/autocraft/bin/autocraft init . --tool claude-code --team starter
   ```
5. **Start Claude Code** and begin:
   ```bash
   claude
   ```
   then type `/start`.

**Even easier:** skip steps 3–4. Start `claude` in the empty folder and paste the [bootstrap prompt](../bootstrap-prompt.md). The *Team Builder* agent interviews you and does the setup for you.

---

## Path B — Claude app (Code session on web or phone)

Claude's **Code** sessions run in the cloud against a GitHub repository, so you need no terminal. The same agents and `/commands` work, and sub-agents run in parallel.

**One-time:** connect **GitHub** to Claude (Settings → connect, or claude.ai/connect-github) and allow access to your project repository. (`sak-io/autocraft` is public; the session can clone it without special access.)

**If you already have written documents** (a product concept, a technical plan) in your repo — the best case — follow **[Kick off a project from your own documents](../kickoff-existing-docs.md)**: add one small `CLAUDE.md` pointer to the repo, start a Code session on it, and type *"Kick off this project with autocraft."*

**If you only have an idea:**
1. On github.com (or the GitHub app) create a **new, empty, private repository**.
2. In the Claude app open **Code → New session → select that repository**.
3. Paste the first prompt from the [bootstrap prompt](../bootstrap-prompt.md). The Team Builder interviews you, installs the team, and commits it to the session's branch as one separate install commit. Then type `/start`.

> **Today's limits (Path B)**
> - The team commits to the single branch your session was given and **does not open pull requests or push other branches unless you ask** (`git_mode: session-branch`). Say *"open the pull request"* when you are ready to merge.
> - Cloud sessions have GitHub *tools* rather than the `gh` command; the roles adapt (protocol §13).
> - A full run from the phone app has not yet been rehearsed end to end; please report anything that surprises you.
> - Work is saved at each step. If a session ends for any reason, continue in a new one with `/status`.

---

## Path C — Claude app chat Project (no code, no repo)

Good for specs, designs, and reviews.

1. In claude.ai create a **Project**.
2. Paste the **chat prompt** from the [bootstrap prompt](../bootstrap-prompt.md) into the Project instructions.
3. Say: *"Let's start. I want to build …"*
4. The assistant plays one role at a time ("Acting as: requirements-analyst"). **For reviews, open a new chat in the same Project** and paste only the spec and the work — that gives you the independent review the guide keeps promising.

Chat can't run code. It will give you commands to run elsewhere. When you're ready to build for real, move to Path A/B and bring your spec along.

---

## Path D — Other tools

Run the setup once, naming your tool:
```bash
python3 ~/autocraft/bin/autocraft init . --tool cursor        # or: copilot, gemini-cli, windsurf, cline, agents-md, prompts
```
Then follow the one-page guide for your tool: [Cursor](../tools/cursor.md) · [Copilot](../tools/copilot.md) · [Gemini CLI](../tools/gemini-cli.md) · [Windsurf](../tools/windsurf.md) · [Cline](../tools/cline.md) · [Codex / AGENTS.md](../tools/agents-md.md) · [any chat](../tools/prompts.md).

Tools without real sub-agents run the team as **role hats**: one role per session, and **a fresh session for every reviewer**.

---

## How do I know it worked?

After setup you should see (Path A/B):
- a `.claude/agents/` folder with one file per role,
- a `.claude/skills/` folder (the `/commands`),
- a `CLAUDE.md` file describing your team,
- a `.autocraft/config.yml` file with your choices.

Type `/status`. If the team answers with a short status board, you're ready.

**Next:** [3. Your first project →](3-your-first-project.md)
