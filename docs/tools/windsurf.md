# Windsurf

Generated in `.windsurf/rules/`: `autocraft-team.md` (always on), `role-<id>.md` (model-decided by description), `workflow-<id>.md` (manual).

```bash
python3 autocraft/bin/autocraft init . --tool windsurf --team web-product
```
**Use:** rules attach automatically; invoke a workflow by mentioning its rule (*"@workflow-start"*). New Cascade session for every reviewer. Windsurf also reads `AGENTS.md` (add `agents-md` to share with teammates on other tools). Rule files have size limits — keep custom rules short.
