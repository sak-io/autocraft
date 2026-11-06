# Cline

Generated: `.clinerules/autocraft-team.md` (team guide, always loaded) plus `.autocraft/roles/` and `.autocraft/workflows/` read on demand (keeps Cline's context small).

```bash
python3 autocraft/bin/autocraft init . --tool cline --team starter
```
**Use:** *"Follow the autocraft team guide: run the start workflow."* To work as a role: *"Act as the developer — read .autocraft/roles/developer.md."* Reviews in a new task.
**Guardrails:** autocraft generates no permission or hook file for Cline; the protocol's production gate and irreversible-command rules are instructions here. Back them with branch protection (`scripts/onboard-repo.sh`) and any setting your tool offers. See [enforcement per tool](../ai-native-sdlc.md#enforcement-per-tool).
