# Customizing

## Tune strictness
Edit `.autocraft/config.yml`: `autonomy_level`, `max_review_rounds`, `max_parallel_developers`, `human_owner`.

## Change or add a stack
1. Add `templates/github/workflows/ci-<stack>.yml` (flutter already included) (job must be named `ci`).
2. Add the stack to `scripts/install.sh` (`--lang` case, CodeQL language, Dependabot ecosystem).
3. Mention stack-specific lint/test commands in `repo-onboarder`.

## Add a capability
Copy `capabilities/authentication.md`, keep its six headings, add a row to `capabilities/README.md`. Trigger words drive automatic detection in `/discover`.

## Add an archetype
Copy `archetypes/api-service/archetype.md` to `archetypes/<name>/archetype.md`, rewrite each section (the headings are required — `validate.sh` checks), and add the name to the table in `archetypes/README.md`. All agents pick it up automatically via `.autocraft/config.yml → archetypes`. Add a CI template if the stack is new.

## Add an agent
Create `.claude/agents/<name>.md`:
```markdown
---
name: <name>            # must equal the filename
description: <when to use it — this is how Claude decides to delegate>
tools: Read, Grep, Glob # least privilege; add Write/Edit/Bash only if needed
model: inherit
---
<role, inputs, outputs, checklist, rules, handoff>
```
Ideas: `ux-designer`, `data-engineer`, `devops-engineer` (deploy/IaC), `technical-writer`, `performance-engineer`, `compliance-reviewer`. Then wire it into a skill (`.claude/skills/*/SKILL.md`) and add a row in `README.md`. Run `bash scripts/validate.sh`.

## Add a workflow
Create `.claude/skills/<name>/SKILL.md` with `name`/`description` frontmatter. Write the loop explicitly (who runs, in what order, exit conditions, round limit).

## Make an agent stricter or more lenient
Edit its checklist and severity guidance. Keep one rule fixed: **humans merge**.

## Keep your project updated
Re-run `install.sh` on your project: agents/skills are overwritten with the latest; your `CLAUDE.md`, config, and `.github` files are kept (never clobbered).
