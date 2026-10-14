# Lean orchestration: spending fewer tokens, and handing work between AI tools

Origin: a real project (a 30-task mobile app built with a wide parallel team) exhausted a rolling Claude usage limit in roughly 30-40 minutes of work, and was resumed several times after limit resets. Figures below are from that experience and are **estimates**, not measurements.

## Where the tokens went
1. **Long briefs and re-reading.** Every agent started by reading large plan/spec documents. Fix: a *task card* is the whole brief; read only what it names.
2. **Review rounds on every task.** Same-size review for a docs-level change and a safety validator. Fix: **risk tiers** - tier S full loop, tier N one light pass.
3. **CI round-trips as the compiler.** When the cloud session has no toolchain, each CI failure costs a full agent cycle. Fix: batch several tasks per CI run, keep a `LESSONS.md` of known pitfalls that every builder reads, and grep for exhaustive `switch` over changed enums before pushing.
4. **Premium model for review and routine work.** Fix: reviewers/auditors on a mid-tier model; builders on the session model.
5. **Unbounded parallelism.** Wide teams burn the window faster than the work finishes. Fix: cap concurrent agents (2 worked well) and keep the lead's own context small by relying on files, not chat memory.
6. **State in chat.** A limit reset or a different tool lost context. Fix: the state is files in git.

## The agent-agnostic board
`autocraft board init` installs `scripts/board.py` (stdlib Python), `work/{tasks,status}`, `AGENTS.md`. State per task is one small JSON file, so two agents never conflict; a claim is a git push (first push wins); a claim without a heartbeat for `lease_hours` is free again. `AGENTS.md` is read natively by Codex, Cursor and Copilot; Claude Code reads it via the `CLAUDE.md` pointer; chat tools (ChatGPT, Grok, ...) are given `AGENTS.md` + the card and ask a human to run git. The one rule for all of them: **only take tasks that `board.py next` lists.**

## Checklist
- Cards self-contained, with `needs`, `tier`, `verify`.
- `board.py check` in CI (cheap) so BOARD.md and statuses cannot drift.
- Docs/board-only commits skip the heavy CI (`paths-ignore: work/**`).
- Record each CI pitfall in `work/LESSONS.md` the first time.
