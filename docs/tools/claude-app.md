# Claude app — chat Projects (including mobile)

**Two ways to use Claude in the app — pick by what you need:**

| You want | Use |
|---|---|
| To think, plan, write specs, review designs, learn — no repo | **Chat Projects** (this page) |
| Real code, tests, branches, PRs on a repo | **Claude Code sessions** (web / app) → [claude-code](claude-code.md) |

## Chat Projects setup
```bash
python3 autocraft/bin/autocraft init ~/code/my-app --tool claude-app --team starter
```
This writes `claude-project/INSTRUCTIONS.md` and `claude-project/knowledge/*.md` (roles, workflows, protocol, your software-type profile, capabilities). Don't have a computer handy? Ask the Team Builder in any Claude chat: paste the chat prompt from the [bootstrap prompt](../bootstrap-prompt.md).

1. In claude.ai create a **Project**; paste `INSTRUCTIONS.md` into the project instructions.
2. Upload the `knowledge/*.md` files as project knowledge.
3. Start a chat: *"Let's start."* The Team Lead interviews you and plays each role in turn, announcing `Acting as: <role>`.

## Getting real independence in chat
One model playing all roles in one chat is weaker than separate agents. To keep review honest: **open a new chat in the same Project for every reviewer role** and paste only the spec + the work to review. The Team Lead tells you when to do this.

## Limits (be aware)
Chat can't run code or tests — it gives you the commands to run. Use it for discovery, specs, architecture and reviews, then move implementation to Claude Code with the same team (your specs carry over as files).
