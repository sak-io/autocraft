# Plain prompts — ChatGPT, any chat, any model

```bash
python3 autocraft/bin/autocraft init . --tool prompts --team starter
```
Generated: `prompts/00-team-lead.md` (paste first), `prompts/<role>.md`, `prompts/workflows/<workflow>.md`.
**Use:** paste the team-lead prompt, then the role you need. For reviews open a **new conversation** and paste only the spec and the work. No install possible at all? Use the chat prompt in [bootstrap-prompt.md](../../user/bootstrap-prompt.md).
**Guardrails:** autocraft generates no permission or hook file for plain prompts; the protocol's production gate and irreversible-command rules are instructions here. Back them with branch protection (`scripts/onboard-repo.sh`) and any setting your tool offers. See [enforcement per tool](../ai-native-sdlc.md#enforcement-per-tool).
