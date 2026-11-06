# GitHub Copilot

Generated: `.github/agents/<role>.agent.md` (custom agents), `.github/prompts/<workflow>.prompt.md` (prompt files), and a managed block in `.github/copilot-instructions.md`.

```bash
python3 autocraft/bin/autocraft init . --tool copilot --team api-backend --archetype api-service
```
**Use:** in Copilot Chat (VS Code / github.com) pick a custom agent from the agent picker (e.g. `architect`); run workflows as prompt files (`/start`, `/build-feature`). Use a separate chat for each reviewing role. Copilot's coding agent on GitHub issues also reads the repo instructions and agents.
**Note:** custom-agent frontmatter/tool names follow GitHub's current docs; if Copilot rejects a tool name, edit the `copilot` exporter in `bin/autocraft` and `sync`.
**Guardrails:** autocraft generates no permission or hook file for Copilot; the protocol's production gate and irreversible-command rules are instructions here. Back them with branch protection (`scripts/onboard-repo.sh`) and any setting your tool offers. See [enforcement per tool](../ai-native-sdlc.md#enforcement-per-tool).
