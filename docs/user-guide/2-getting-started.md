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

## What every path needs (once)

- A **GitHub account** (free is fine) — except Path C.
- The `autocraft` repository (ask whoever shared this guide for access if it is private).
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

Claude's **Code** sessions run in the cloud against a GitHub repository, so you need no terminal. The same agents and `/commands` work.

**One-time:**
1. In the Claude app go to Settings → connect **GitHub** (the app will link you to claude.ai/connect-github) and allow access to the repository you will use.
2. On github.com (or the GitHub mobile app) **create a new, empty, private repository** for your project, e.g. `my-project`.

**Each project:**
3. In the Claude app open **Code** → start a **new session** and **select your repository** (repositories are chosen when the session starts).
4. Paste the [bootstrap prompt](../bootstrap-prompt.md) (the first block). The Team Builder will ask for access to `autocraft` if needed, interview you, install the team into your repository, and commit it.
5. When it says the team is installed, type `/start`.

> **Today's limits (Path B)**
> - The team commits to the single branch your session was given; it does **not** open extra branches or pull requests unless you ask. Parallel builders work in isolated copies and are merged back for you.
> - Cloud sessions have GitHub *tools* rather than the `gh` command. Roles that mention `gh` will use whatever the session provides; if a step fails, say *"do that with the GitHub tools"*.
> - The repository must exist before you start. You can't create one from inside the session unless you ask the agent to (it can, with your OK).
> - Every command or file change may need your approval tap. In the session settings you can pre-approve routine commands — see the FAQ.

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
