# New to software? Start here

You have an idea. You may never have heard of "CI", "architecture" or "pull requests". That's fine — this framework was built so you don't have to know them. The agents do the engineering; **you make the decisions that are genuinely yours** and approve the result.

## What building software actually involves (the "SDLC" in ten lines)
1. **Decide what to build** (requirements) — who is it for, what must it do, what is *not* included.
2. **Design it** (architecture) — how the parts fit together, where data lives, what could go wrong.
3. **Get a safe workshop** (repository, tests, security scans) — so mistakes are caught automatically.
4. **Build it in small steps** (development) — each step comes with tests that prove it works.
5. **Have someone else check it** (code review) — a fresh pair of eyes finds what the author missed.
6. **Final check before release** — migrations, settings, rollback plan, documentation.
7. **Release** — you press the button.
8. **Keep it healthy** — monitoring, updates, security scans, fixes.

Professional teams use specialists for each step. Here, each specialist is an agent (see the [team](../README.md#the-team)).

## Your first 10 minutes
```bash
git clone https://github.com/sak-io/autocraft.git
bash autocraft/scripts/install.sh ~/code/my-idea
cd ~/code/my-idea && claude
```
Then type **`/discover`** and describe your idea like you'd tell a friend:

> *"I want a website where my yoga students can book classes and pay online, and I get an email when someone books."*

The agents answer in plain words: *"You're building a **fullstack-app** (screens + server + database), which needs **authentication**, **payments**, **database** and **email**. I'd skip a mobile app for now…"* Confirm, then type **`/start`**.

## What you'll be asked (and what you won't)
**You will be asked:** what it should do and for whom, what's in/out of the first version, money and legal decisions (payments, personal data, children), accounts to create (GitHub, a domain name, hosting), and to approve the design and every release.
**You will not be asked:** which database, framework or test library to use. Agents recommend a sensible default, explain it in a sentence, and record it.

## Words you'll hear
Type **`/explain <anything>`** whenever something is unclear: a file, a review comment, an error, or a word. There's also the [glossary](glossary.md). The most important ones:
- **Pull request (PR):** a proposed change waiting for review. The unit of progress.
- **CI:** robots that run all the checks on every change.
- **Review comment severities:** `BLOCKER`/`MAJOR` = must fix · `MINOR` = should fix · `NIT` = taste.
- **`release-ready`:** reviewed, tested, checked — only *you* are left.

## How to know things are going well
- Each PR is **small** (you can skim the summary in a minute).
- **Tests are added with every change** and CI is **green**.
- Reviewer and developer **disagree, then converge** (that's the process working). After 3 rounds they stop and ask you.
- You hear "release-ready" and the PR shows a **Pre-release check** table with no ❌.
- `/status` always tells you in plain words what's happening and whether you need to act.

## Your job as the owner
1. Say what you want, in your own words, and what you *don't* want.
2. Answer the (few) questions — "default" is a valid answer.
3. Read the plain-language summaries. If anything worries you: `/explain`.
4. Approve and merge only when you understand what ships and the checklist is green.
5. **Never paste passwords or API keys into chat or code.** If you do, say so immediately so the key can be rotated.

## Common beginner traps (the agents will push back on these)
| Temptation | Why the agents refuse |
|---|---|
| "Skip the tests, just make it work" | Untested code breaks silently and costs more later |
| "Let everyone be admin" | One mistake or leaked account exposes everything |
| "Build all features at once" | Big changes can't be reviewed; start with a tiny working version |
| "Store card numbers ourselves" | Illegal-adjacent and dangerous — a payment provider does it |
| "Put the API key in the code" | Keys in code get stolen within hours |
| "Edit the live database by hand" | No history, no undo — use migrations |

## What the agents can't do for you
They can't know your customers, decide your pricing, hold legal responsibility, or guarantee there are no bugs. For regulated areas (health, finance, children's data) bring in a qualified professional — the agents will flag when.
