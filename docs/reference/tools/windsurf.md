# Windsurf

Generated in `.windsurf/rules/`: `autocraft-team.md` (always on), `role-<id>.md` (model-decided by description), `workflow-<id>.md` (manual).

```bash
python3 autocraft/bin/autocraft init . --tool windsurf --team web-product
```
**Use:** rules attach automatically; invoke a workflow by mentioning its rule (*"@workflow-start"*). New Cascade session for every reviewer. Windsurf also reads `AGENTS.md` (add `agents-md` to share with teammates on other tools). Rule files have size limits — keep custom rules short.
**Guardrails:** autocraft generates no permission or hook file for Windsurf; the protocol's production gate and irreversible-command rules are instructions here. Back them with branch protection (`scripts/onboard-repo.sh`) and any setting your tool offers. See [enforcement per tool](../ai-native-sdlc.md#enforcement-per-tool).
