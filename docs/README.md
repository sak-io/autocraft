# autocraft documentation

Start with the group that matches what you want to do.

## Using autocraft

| I want to | Read |
|---|---|
| Build something and I'm new to software | [New to software? Start here](user/vibe-coders.md), then the [user guide](user/guide/README.md) |
| Get the commands for my kind of project | [Pick your path](user/guide/0-pick-your-path.md) |
| Follow a full guide from install to merge | [User guide](user/guide/README.md) (pages 0 to 8) |
| Start from documents I already wrote | [Kick off from your own documents](user/kickoff-existing-docs.md) |
| Let an agent set up the team for me | [Bootstrap prompt](user/bootstrap-prompt.md) |
| Look up a word | [Glossary](user/glossary.md) |
| See an API example, narrated | [Order API walkthrough](user/example-order-service.md) |

## Reference (how it behaves)

| Topic | Read |
|---|---|
| What the agents may and may not do, and what is enforced | [Guardrails](reference/guardrails.md) |
| Handoffs, review rules, labels, autonomy levels | [Collaboration protocol](protocol.md) |
| Change roles, teams, rules; extend the framework | [Customizing](reference/customizing.md) |
| The stages a project goes through | [Lifecycle](reference/lifecycle.md) |
| Why a team, and how to run it in any tool | [Orchestration patterns](reference/orchestration-patterns.md) |
| Spend fewer tokens; the task board | [Lean orchestration](reference/lean-orchestration.md) |
| Two real builds compared | [Lean vs thorough](reference/lean-vs-thorough.md) |
| Review a very large pull request | [Reviewing large PRs](reference/reviewing-large-prs.md) |
| Set up for a specific AI tool | [Tool pages](reference/tools/) (Claude Code, Claude app, Cursor, Copilot, Gemini CLI, Windsurf, Cline, AGENTS.md, plain prompts) |

## Examples

[ClassBook](../examples/classbook/README.md) (thorough build), [Receipt Tally](../examples/receipt-tally/README.md) (lean build), [Pantry Pal kickoff](../examples/pantry-pal-kickoff/README.md) (documents first).

## Contributing to autocraft

See [Contributing and validation](../README.md#contributing-and-validation) and the "extend the framework" section of [Customizing](reference/customizing.md#extend-the-framework-itself-contribute). Run `bash scripts/validate.sh` before opening a pull request.

`protocol.md` stays in this folder because the CLI copies it into every project it installs.
