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

## Lessons from a 31-task Claude Code run (cloud session, lead + worktree agents)
Origin: Engram (a stdlib-only Python daemon + MCP server), built from two owner documents with `kickoff`: lean team + architect + QA, tiered review, at most 2 parallel developers. Roughly 1.2 M subagent tokens for 21 core tasks. Concrete, repeatable findings:

**Token levers that mattered**
- `autocraft init --token-saver` sets the settings below in one flag (reviewers, QA, auditor and analyst on a mid-tier model, 2 review rounds, 2 parallel developers). Builders and architect inherit the session model.
- A task card as the entire brief ("read the card + `lessons.md`, nothing else") kept builder runs at 25-60 k tokens. Reading both source documents again cost ~80 k per agent.
- Ask for hand-backs under N words, with a fixed shape (branch, commit, verify result, caveats). The lead's context stayed small enough to run 20+ tasks in one session.
- Gate slow benchmarks behind an env flag (`ENGRAM_SLOW_TESTS=1`). A default suite that grew to 90 s was paid by every builder and reviewer on every task.
- Tier S (security/safety-critical) tasks got a full review loop; tier N one light pass. The full loop found real defects in 8 of 11 tier S tasks (false merges in the dedup rule, ReDoS in three modules, an unsafe prune, lock starvation, an auth lockout), so do not cut it for those. A narrow, mechanical fix after round 2 can be verified by the lead with the reviewer's own script instead of a third review round.

**Orchestration hygiene (each of these cost real time)**
1. *Reviewers must never check out a branch in the lead's main working tree.* One did (`git checkout t08`), which silently detached the lead's HEAD; later `git push origin <branch>` calls pushed a stale ref (silent no-ops) while all merges sat unpushed. Tell reviewers to use `git worktree add /tmp/chk <base> --detach && git merge --no-edit <branch>` and remove it afterwards.
2. *The lead asserts the branch before every merge/push* (`test "$(git branch --show-current)" = <branch>`), and pushes `HEAD:refs/heads/<branch>`, then compares `git rev-parse HEAD origin/<branch>`.
3. *Worktree agents may start from a stale ref.* Several `isolation: worktree` agents found `git checkout -B tNN <integration-branch>` resolved to an old commit. Put in every brief: "verify `git log --oneline -1` is the expected merge commit, else `git merge <integration-branch>`".
4. *Hand-backs can be garbage* (one just said "pending"). Check the branch state (`git log base..branch`, `git status`) before trusting or re-running an agent.
5. *Process kills:* `pkill -f <name>` can match the lead's own shell command line. Record pids, or use a `[e]ngram`-style pattern.
6. *Adversarial review prompts beat checklists.* Telling the reviewer "write 30 pairs of your own that your fix could still miss" found a second false-merge class after the first fix, which the fixture suite had passed.
7. *Round limits:* after the configured rounds, either escalate or verify mechanically; say which you did. A reviewer's severity can be a misreading ("15 tokens per pair" read as "15 pairs per category"): check before obeying.
8. *Ask-question tools cap at 4 questions per call*; `kickoff` was changed from "5" accordingly.
