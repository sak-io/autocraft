# Claude Code (terminal, desktop, web, Claude app code sessions)

**Best fit.** Claude Code has real sub-agents and slash-command skills, so the team runs as designed: each role is its own agent with its own context and tool permissions.

## Set up
```bash
python3 autocraft/bin/autocraft init ~/code/my-app --tool claude-code --team web-product --archetype fullstack-app
cd ~/code/my-app && claude
```
Generated: `.claude/agents/<role>.md` (one subagent per role, tools restricted by ability), `.claude/skills/<workflow>/SKILL.md` (the slash commands), and a managed block in `CLAUDE.md` (team guide + rules; your own `CLAUDE.md` text is preserved).

## Use
- Type **`/start`** for a new project, **`/build-my-team`** to (re)configure, **`/status`** any time, **`/explain <anything>`** when lost.
- Delegate by name: *"Use the architect subagent to design this from docs/specs/…"*. Reviews: *"Use the pr-reviewer subagent on PR 12."*
- Sub-agents can't call each other, so the main session runs the loops (author → reviewer → author) and enforces the round limit — the workflows spell this out.
- Parallel builders: ask for several `developer`/`backend-developer`/`frontend-developer` agents on **independent** tasks (worktree isolation recommended).

## On the web or the Claude mobile app
Claude Code sessions on claude.ai/code (and in the Claude app) run in a cloud container against your GitHub repo. Commit the generated files, select the repo when starting a session, and the same team loads. Cloud sessions use GitHub tools instead of the `gh` CLI for PR work; the `repo-onboarder`'s shell script needs `gh`, so run `autocraft github` locally or follow its checklist manually.

## Update / customize
`python3 .autocraft/framework/bin/autocraft sync` after editing `.autocraft/config.yml` or `.autocraft/custom/`. See [customizing](../customizing.md).
