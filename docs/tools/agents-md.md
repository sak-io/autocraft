# AGENTS.md — Codex, Jules, Aider, Zed, and most other agentic tools

`AGENTS.md` is the open, tool-neutral convention for agent instructions. autocraft writes a managed block into it (team guide, rules) and neutral role/workflow files in `.autocraft/roles/` and `.autocraft/workflows/`.

```bash
python3 autocraft/bin/autocraft init . --tool agents-md --team starter
```
**Use:** *"Follow AGENTS.md. Act as the requirements-analyst (read .autocraft/roles/requirements-analyst.md) and run the start workflow."*
- **OpenAI Codex CLI / Jules / Zed / many others** read `AGENTS.md` automatically.
- **Aider:** `aider --read AGENTS.md --read .autocraft/roles/developer.md`.
- Combine with a native export for your main tool (`--tool claude-code,agents-md`) so teammates on other tools get the same team.
