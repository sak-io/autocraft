# Customizing your agent team

Your team is plain files. The rule: **edit config and `.autocraft/custom/`, never generated files** (they are overwritten on `autocraft sync`). Run the CLI from your project with `python3 .autocraft/framework/bin/autocraft <command>`.

## The knobs (`.autocraft/config.yml`)
| Key | What it does |
|---|---|
| `tools` | which AI tools get files (`claude-code, claude-app, cursor, copilot, gemini-cli, windsurf, cline, agents-md, prompts`) |
| `team` | one or more teams: `starter, web-product, api-backend, mobile, ai-product, data-ml, platform, toolsmith, makers` |
| `roles_add` / `roles_remove` | fine-tune the roster |
| `archetypes`, `capabilities` | what you build / what it needs → agents apply those profiles |
| `experience` | `beginner / intermediate / expert` — how agents explain and decide |
| `autonomy_level`, `max_review_rounds`, `max_parallel_developers` | how often you're asked, loop limits, parallelism |

## Common changes
| I want to… | Do |
|---|---|
| Start lean, add specialists later | `autocraft init . --team starter` … later `autocraft add-role qa-engineer` |
| Combine software types | `--team mobile,ai-product` |
| Use a second AI tool | `autocraft add-tool cursor` |
| House rules for everyone | write `.autocraft/custom/team-rules.md` |
| House rules for one role | write `.autocraft/custom/roles/<id>.append.md` |
| Replace a role entirely | copy `.autocraft/framework/roles/<id>.md` to `.autocraft/custom/roles/<id>.md`, edit |
| Invent a role | `autocraft new-role security-champion`, edit, `autocraft add-role security-champion` |
| Custom workflow | add `.autocraft/custom/workflows/<id>.md` (frontmatter `id`, `description`) and list it in a team |

Then `autocraft sync` and `autocraft doctor`.

## Keep these fixed
Independent review, tests with every change, no secrets in code, and **humans merge**. `doctor` warns if your team has no reviewer or builder.

## Extend the framework itself (contribute)
- **Role:** add `roles/<id>.md` (frontmatter `id, title, category, abilities, description`), list it in the right `teams/*.md`.
- **Team:** add `teams/<id>.md` (`roles`, `optional`, `workflows`, `fits`, and a playbook body).
- **Archetype / capability:** copy an existing profile and keep its headings.
- **Another AI tool:** add an `export()` branch in `bin/autocraft`, an entry in `TOOLS`/`HOWTO`, and `docs/tools/<tool>.md`. `scripts/validate.sh` checks it all.
- **Another language's CI:** add `templates/github/workflows/ci-<lang>.yml` and an entry in `LANGS` in `bin/autocraft`.

## Update the framework
Pull the latest autocraft, then `python3 <clone>/bin/autocraft sync <your-project>` — it re-vendors the framework and regenerates files; your config and `custom/` are untouched.
