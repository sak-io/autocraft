# 7. Give feedback

Thank you for testing. You are not being tested — **the guide is**. Anything that confused you, slowed you down, or turned out to be untrue is a bug in the guide or the product, and we want to hear it.

## What we want to learn

1. **Can a technical non-developer get from zero to a working team without help?**
2. **Where do people get lost, bored, or nervous?**
3. **Do the agents' outputs make sense to a non-developer?**
4. **Do you trust the result enough to ship it — and if not, what would change that?**

## Before you start (5 minutes)

Tell us (anonymous is fine):
- Your role (e.g. analyst, designer, ops, founder): ______
- Experience with AI assistants (never / sometimes / daily): ______
- Experience with software development (none / some scripting / professional developer): ______
- Which track will you follow? **New to software** (pages 1–5) / **Software professional** (pages 1, 2, 6, 5): ______
- The tool you'll use (Claude Code terminal / Claude app / other): ______

## The test (about 60–90 minutes)

Do the tasks in order. **Think out loud** (or jot notes): say what you expected, what you did, and what happened. Don't ask for help until you've tried the guide, the FAQ, and `/explain`. Note the time you got stuck and what unstuck you.

| # | Task | Done when | Note |
|---|---|---|---|
| 1 | Read page 1 ([the idea](1-the-idea.md)) | You can explain "why a team" to a colleague in two sentences | Time: ___ |
| 2 | Follow [Getting started](2-getting-started.md) for your path | You typed `/status` and got a status board | Where did you hesitate? |
| 3 | Describe a small idea of your own (a booking form, a tracker, a calculator, a bot…) with `/discover` | You agree (or disagree, and said why) with the recommended software type | Did the explanation make sense? |
| 4 | Choose lean or fuller team | Team installed | Did you understand the choice? |
| 5 | Run `/start`; answer the spec questions | You approved a spec | Were the questions clear? Too many? |
| 6 | Approve the plan | You said "approved" | Could you tell what you were approving? |
| 7 | Run `/build-feature` for **one** task | You read the 3-line summary and one review | Did the review make sense? Did you trust it? |
| 8 | Ask `/explain` about something you didn't understand | You got a clearer answer | Was it clear? |
| 9 | (Optional) change the team: add a role or a house rule | `autocraft doctor` says OK | Was it discoverable? |
| 10 | Say what you'd need before sharing the result with real users | A list | |
| 11 | *(software professionals)* Define your own small team (`.autocraft/custom/teams/…`), add one house rule in `team-rules.md`, give one role a different model, then `autocraft sync && autocraft doctor` | You can show the generated files changed accordingly | Was it discoverable? What did you expect to be able to do that you couldn't? |

## Questions (rate 1–5, 5 = best; add a sentence for any 1–3)

**The guide**
1. The guide told me what to do next at every step. ___
2. I understood the words used (or `/explain`/glossary helped). ___
3. The length and level of detail were right. ___
4. What was the single most confusing sentence or step? ______
5. What is missing that you looked for and couldn't find? ______

**The product**
6. Setting up the team was easy. ___
7. I always knew what the agents were doing and what I had to do. ___
8. The summaries and reviews were understandable. ___
9. I felt in control (could say no, change direction). ___
10. I would trust the output enough to show it to a real user. ___ — what would raise this? ______

**If you're a software professional** (also answer these)
- I could pick, remove and customize roles without reading the source. ___
- The loop (independent reviewer, severity tags, round limits, file handoffs) matches how I'd want AI-assisted work to be controlled. ___
- Which role would you replace or add first, and why? ______
- What would stop you from using this on a real codebase (permissions, cost, trust, lock-in, missing integration)? ______
- What is the first thing you'd automate or tighten with `team-rules.md`? ______

**Overall**
11. Would you use this for a real project? (yes / maybe / no) — why? ______
12. Who else do you think it's for, and who is it *not* for? ______
13. One thing to **keep**, one to **change**, one to **add**: ______

## Bug report template (copy/paste)

```
Where: (guide page + heading, or command)
What I did:
What I expected:
What happened:
Tool + version (e.g. Claude Code 2.x on macOS / Claude app on iPhone):
Output of `autocraft doctor` (if relevant):
```

## How to send it

Send your notes (a message, a document, or screenshots) to the person who shared this guide with you. Screenshots of confusing screens are gold.
