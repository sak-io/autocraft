---
name: build-feature
description: Implements a work item end to end - developer writes code plus unit and integration tests and opens a PR, then pr-reviewer and developer iterate until the reviewer approves. Can run several independent tasks in parallel.
---

# /build-feature [task id or description]

1. **Pick work.** Read `docs/architecture/work-breakdown.md` and open PRs. Choose the next task whose dependencies are merged (or the one the human named). For parallel work, choose only tasks that are independent and touch different files; cap at `max_parallel_developers` (config, default 3).
2. **Develop.** Invoke `developer` (one per task, in parallel if several; use `isolation: worktree` so they don't collide). Each opens a PR labelled `agent:needs-review`.
3. **Review loop** — for each PR:
   ```
   round = 1
   loop:
     Invoke `pr-reviewer` on the PR (round number, previous comments)
       VERDICT: APPROVED           -> exit loop (label agent:approved)
       VERDICT: CHANGES REQUESTED  -> Invoke `developer` with PR number + instruction to address every comment
                                      round += 1; if round > max_review_rounds -> label needs-human, escalate
   ```
4. **Hand-off.** When approved, tell the human which PRs are approved and proceed to `/release-check` for each.

## Quality bars you enforce
- A PR with no unit tests or no integration tests (where a boundary is crossed) goes straight back to the developer.
- CI must be green on the latest commit before each review round starts.
- Never merge. Never skip a loop round.

After each PR, give the human a 3-line summary: what was built, test evidence, review rounds taken.
