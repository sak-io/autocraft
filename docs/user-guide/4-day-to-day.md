# 4. Day to day

## Cheat sheet

| I want to… | Type |
|---|---|
| See where things stand and what I need to do | `/status` |
| Start a new project | `/start` |
| Work out what kind of software I'm building | `/discover` |
| Build the next task | `/build-feature` |
| Have a change reviewed | `/review-pr <number or branch>` |
| Check a change before release | `/release-check` |
| Get a big change ready for a human to review | `autocraft review-map`, then `/review-guide` if it recommends one ([details](../reviewing-large-prs.md)) |
| Check security | `/security-scan` |
| Understand anything (a file, a comment, an error, a word) | `/explain <it>` |
| Change my team | `/customize-team` |
| Set up a team from scratch | `/build-my-team` |

(Names are the same in every tool; in tools without slash commands, say *"run the build-feature workflow"*.)

## A normal session

1. Open your tool in the project. Type `/status`.
2. The answer has four parts: **where we are**, **what's in flight**, **what's blocked**, **what you need to do**. If "what you need to do" is empty, you can just say *"continue"*.
3. Approve or answer whatever is waiting. Then `/build-feature`.
4. Close the tab whenever you like. **Everything is saved in your project's files**, not in chat memory, so any later session — even in a different tool — can pick up with `/status`.

## Reading a review without being a developer

Open the review (a file in `.autocraft/work/<task>/` or comments on a pull request). Read in this order:

1. **The verdict line** — `APPROVED` or `CHANGES REQUESTED`.
2. **BLOCKER / MAJOR items** — each should say *what's wrong, where, why it matters*.
3. **The builder's replies** — `Fixed in <commit>` or `Not changing because …`. If a "not changing" sounds weak, ask `/explain` or push back: *"I'd rather you fix this."*
4. **What's good** — reviewers are asked to say what is done well too.

Don't try to judge the code. Judge whether the *findings make sense to you* and whether *the checks are green*.

## Changing your mind

- **Small change** ("make the button say 'Reserve'"): just tell the team. It becomes a new small task.
- **Scope change** ("actually add payments"): say so. The requirements-analyst updates the spec, the architect checks impact, and new tasks are added. Do this deliberately — it is the most common cause of projects that never finish.
- **You disagree with a decision**: say so. Decisions are recorded in `docs/adr/`; agents will write a new decision that supersedes the old one.

## When agents stop and ask you

They stop in four situations. Each time you get the decision, 2–3 options, a recommendation, and the consequence of each:

1. **Gate** — spec, plan, or release needs your approval.
2. **Deadlock** — builder and reviewer disagreed for 3 rounds.
3. **Human-only decision** — money, legal/privacy, accounts to create, safety.
4. **Missing information** — something only you know.

## Doing several things at once

Ask for it: *"Build tasks T2 and T3 in parallel."* The team only does this for tasks that are **independent** (they touch different files and don't depend on each other). Each builder works in its own copy; the results are merged for you. Default maximum is 3 at once (`max_parallel_developers`).

## Keeping safe

- **Never paste passwords or API keys** into chat or files. If you did, tell the team — the key must be replaced, not just deleted.
- The team will refuse shortcuts like "skip the tests" or "let everyone be admin". That's by design — ask `/explain` why.
- Run `/security-scan` before sharing your app with anyone, and roughly weekly while it's live.

## Tips

- **Small tasks beat big tasks.** A change you can describe in one sentence gets better review.
- **Write acceptance criteria in plain words.** "A student can't book a full class" is testable; "bookings should work well" is not.
- **Ask the reviewer's opinion, not just the builder's.** *"Reviewer: what worries you most about this project?"* is a good question at any time.
- **Look at the files.** Everything the agents produce is plain text in your project: `docs/specs/`, `docs/architecture/`, `docs/adr/`, `docs/STATUS.md`. Nothing is hidden.

**Next:** [5. Choosing and customizing your team →](5-choosing-your-team.md)
