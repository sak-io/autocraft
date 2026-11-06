# Cursor

Generated: `.cursor/rules/autocraft-team.mdc` (always-on team guide), `role-<id>.mdc` (agent-requested by description), `workflow-<id>.mdc`.

```bash
python3 autocraft/bin/autocraft init . --tool cursor --team web-product --archetype fullstack-app
```
**Use:** open the folder in Cursor. Roles attach when relevant, or @-mention one: *"@role-architect design this from docs/specs"*. Start a workflow with *"@workflow-start"*.
**Guardrails (generated once, yours afterwards, `sync` never overwrites them):**
- `.cursor/hooks.json` plus `.cursor/hooks/production-gate.py`: a `beforeShellExecution` hook (fail-closed) that blocks production deploys until `RELEASE_APPROVAL` is set, and blocks force-push, push to `main`/`master` and `rm -rf`. Format per [Cursor hooks](https://cursor.com/docs/hooks). The script runs from the project root.
- `.cursor/cli.json`: `Read`/`Write` deny rules for `.env*` and `secrets/**`. Cursor documents these permissions for the **Cursor CLI** only; the editor's agent may not honor them.
- `.cursorignore`: keeps `.env*` and `secrets/` out of the agent's context. Per Cursor's docs it is not absolute: terminal and MCP tools can still read those files.
- Not generated: multi-word `Shell(...)` deny entries (the docs do not specify their syntax), so shell safety rests on the hook. Reports say the hook's "ask" decision is unreliable, so the gate only blocks. If one of these files already exists, it is kept and `init` tells you what to add.

**Independence:** open a **new chat** for each reviewer role (`pr-reviewer`, `principal-engineer`, `release-gatekeeper`, `qa-engineer`) so it doesn't inherit the author's reasoning. Cursor also reads `AGENTS.md`: add `--tool cursor,agents-md` if you share the repo with people on other tools.
