# Cursor

Generated: `.cursor/rules/autocraft-team.mdc` (always-on team guide), `role-<id>.mdc` (agent-requested by description), `workflow-<id>.mdc`.

```bash
python3 autocraft/bin/autocraft init . --tool cursor --team web-product --archetype fullstack-app
```
**Use:** open the folder in Cursor. Roles attach when relevant, or @-mention one: *"@role-architect design this from docs/specs"*. Start a workflow with *"@workflow-start"*.
**Independence:** open a **new chat** for each reviewer role (`pr-reviewer`, `principal-engineer`, `release-gatekeeper`, `qa-engineer`) so it doesn't inherit the author's reasoning. Cursor also reads `AGENTS.md`: add `--tool cursor,agents-md` if you share the repo with people on other tools.
