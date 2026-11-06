# Gemini CLI

Generated: managed block in `GEMINI.md` (team guide), `.gemini/commands/<workflow>.toml` (slash commands), and neutral copies in `.autocraft/roles/` and `.autocraft/workflows/`.

```bash
python3 autocraft/bin/autocraft init . --tool gemini-cli --team starter
gemini
```
**Guardrails (generated once, yours afterwards, `sync` never overwrites them):** `.gemini/settings.json` with a `BeforeTool` hook on `run_shell_command` (runs `.gemini/hooks/production-gate.py`: blocks production deploys until `RELEASE_APPROVAL` is set, and force-push, push to `main`/`master`, `rm -rf`) and `tools.exclude` entries for the same destructive commands. Format per the [Gemini CLI hooks](https://google-gemini.github.io/gemini-cli/docs/hooks/) and settings docs. Notes:
- Gemini asks you to trust project hooks on first run, and again when they change.
- `tools.exclude` is prefix matching and Google calls it not a security mechanism; the hook is the real gate.
- The docs do not state the hook's working directory, so the command uses the relative path from the documentation's own example. If the hook does not fire, run `gemini` from the project root.
- Not generated: workspace policy files (`.gemini/policies`), which the docs say are not loaded, and a secrets-read deny, which has no documented project-level setting. Put those in `~/.gemini/policies` yourself if you need them.
- Google is moving Gemini CLI users to Antigravity CLI; autocraft has not been checked against it.

**Use:** `/start`, `/build-feature`, … (nested names like `/review-pr`). For a role: *"Act as the requirements-analyst — read .autocraft/roles/requirements-analyst.md."* Run reviewers in a **new session**.
