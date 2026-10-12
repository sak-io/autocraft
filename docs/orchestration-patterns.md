# Why a team — and how to run it in any tool

## One agent vs. a team
| | One agent does everything | Agent team |
|---|---|---|
| Blind spots | Reviews its own work → misses its own mistakes | Reviewer didn't write the code → fresh eyes |
| Context | One giant, muddled context | Each role carries only what it needs |
| Quality bar | Drifts as the conversation grows | Each role enforces its own checklist |
| Speed | Sequential | Independent tasks in parallel |
| Your control | Hard to see what happened | Clear handoffs and checkpoints where you decide |

You don't need a big team. The smallest useful one is **builder + independent reviewer** (+ a security check) — the `starter` team.

## Four patterns
1. **Pair (builder ⇄ reviewer)** — the essential loop. Author builds with tests; reviewer (fresh context) finds issues with severity tags; author answers every comment; repeat ≤ N rounds, then ask the human.
2. **Pipeline with gates** — requirements → design (architect ⇄ principal) → build → review → release check. Each gate has an owner and an exit criterion; the human approves the gates that matter.
3. **Parallel builders** — several builders on independent tasks (different files), merged by review. Needs a task list with dependencies and a contract defined first.
4. **Specialist consult** — pull in a role only when a need appears (UX when screens matter, security before shipping, QA when bugs recur, writer before release).

## Running it where sub-agents exist (Claude Code, Copilot custom agents)
Each role is a separate agent with limited tools. The main session (or you) coordinates loops. Roles don't call each other.

## Running it where they don't (Cursor, Gemini CLI, Windsurf, Cline, Codex, chat)
Use **role hats**:
1. One role per session; start with *"Acting as: <role>"* and make the tool read the role file.
2. **Reviewers always get a fresh session** with only the spec, the diff and the protocol — never the author's chat. That one habit preserves most of the benefit of real sub-agents.
3. Pass work through **files**, not memory: specs, `docs/architecture/`, review files (`.autocraft/work/<task>/review-N.md`), `docs/STATUS.md`.

## Handoffs are the contract
Every role ends with a handoff block (from, to, status, artifacts, open items, next) — see [protocol](protocol.md). Because they're text in files, they work in every tool and survive across sessions and people.

## Humans stay in charge
Autonomy levels 1–3 control how often you're asked; **merging and releasing is always yours**. Loops stop after a set number of rounds and ask you instead of grinding.
