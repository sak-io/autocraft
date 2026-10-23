---
id: kickoff
needs: [requirements-analyst]
description: Starts a project from documents the owner already wrote (a product concept and/or technical plan in the repo). Ingests them into a spec, validates the technical plan, gets the owner's approvals, then builds with parallel developers, independent reviewers, QA and a security check. Use when the repo already contains the product documents.
---

# /kickoff – build from the owner's documents

You are the team lead (main session). The owner has already written down *what* and (probably) *how*; your job is to turn that into a reviewed, tested product without making them repeat themselves. Read the team guide in `CLAUDE.md` for how to run agents.

## 0. Preconditions
- The team is installed (`.autocraft/config.yml` exists, `doctor` is OK) and `sources` lists the owner's documents. If not, act as `team-builder` first (`roles/team-builder.md`).
- The framework installation is committed **on its own, before any product work** (`autocraft init ... --commit`; later `autocraft sync --commit`): one commit with only autocraft-owned files. If it is not committed yet, do that first. When the owner wants human review of the PR, offer to open that bootstrap commit as a small separate PR first (the files are marked generated, so they can also be filtered out of review).
- Read every source document yourself first. Summarise to the owner in 5 plain lines: *what I understood you want to build, who it is for, what your technical plan chooses, what I think is missing*.

## 1. Spec (ingest) — `requirements-analyst`
Delegate in **ingest mode**: produce `docs/specs/<name>.md` with citations to the source sections, assumptions, and a **Gaps, ambiguities and contradictions** list with recommended defaults. Show the owner the 5-line summary + the gaps list. 
**Gate:** the owner answers/accepts defaults and confirms the spec ("AGREED"). Phones: ask at most 4 questions per ask (tool limit), each with a default, each with a default.

## 2. Plan (adopt & validate) — `architect` ⇄ `principal-engineer` (if installed; otherwise the builder writes `docs/architecture/plan.md`)
Delegate to the architect in **adopt mode**: the owner's technical choices become ADRs "given by owner"; validate against the spec; fill the missing parts; produce the work breakdown (small tasks, dependency graph, which can run in parallel, required tests per task). The principal-engineer reviews; loop ≤ `max_review_rounds`. 
**Gate:** the owner approves the plain-language summary: what will be built, which of *their* choices were kept, which risks were found and what you recommend changing (the owner decides).

## 3. Build — `/build-feature` per task
- First the walking skeleton / shared foundation task alone; then independent tasks **in parallel** (≤ `max_parallel_developers`), each in its own local worktree, per the Git mode.
- Every task: builder writes code + tests -> a *fresh* `pr-reviewer` runs the tests itself and probes -> builder answers each finding -> re-review. After the reviewer approves, integrate the task (session-branch: `git merge --no-ff` into the session branch) and run the **whole** suite again; fix integration breaks with a small follow-up task.
- Update `docs/STATUS.md` and commit + push after every task.
- The framework install is its own commit (`autocraft init --commit`; see `roles/team-builder.md`, "Pointer-driven kickoff"), made **before** any product work.

## 4. Assurance
- `qa-engineer` (if installed): test plan from the spec's acceptance criteria, traceability matrix, authorization/real-HTTP/e2e tests, exploratory testing; defects become failing tests; builders fix; reviewer re-checks each.
- `security-auditor`: run the scanners that exist, review against the threat model, report by severity. Fix MEDIUM and above before release.

## 5. Release gate — `/release-check`
`release-gatekeeper` checks what review can't (migrations, config, rollback, docs). Then tell the owner, in plain words: **what ships, the risk, how to undo it, and what only they can do** (accounts to create, secrets to set, the pull request to merge). Open the session branch's pull request **only if the owner asked**; otherwise say the branch is ready.

## 6. Map the diff (last step before the owner merges)
**Before telling the owner to merge: map the diff.** Run `python3 .autocraft/framework/bin/autocraft review-map` (free; no model tokens). If `guide_recommended` is true in `--json`, run `/review-guide` (a fresh `pr-reviewer` writes `docs/review-guide.md`; every reference is script-verified) and link it at the top of the pull request description. If `split_recommended` is true (the diff exceeds twice the thresholds), also **offer** the owner the stacked-PR split (`review-map --slices`) and do it only after an explicit yes. See `docs/reviewing-large-prs.md`.

## Always
- Never edit the owner's source documents; raise changes as questions.
- Report progress compactly after each step (what happened, what's next, whether the owner is needed). Use `/status` to resume in a new session.
