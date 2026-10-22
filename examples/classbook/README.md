# Worked example: ClassBook — a booking app for a yoga studio

A real project, built by following the [User Guide](../../docs/user-guide/README.md). Every file under [`project/`](project/) was produced by the agent team; every decision, disagreement and defect below really happened.

> **How to read this page:** each step shows **what you (the owner) do**, **what the agents do**, and **what you see**, with links to the real artifacts. Read it top to bottom to see the whole journey, or jump to the [results](#results-at-a-glance) and [what went wrong](#what-went-wrong-and-what-we-changed-because-of-it).

## Honest notes before you start

- **The owner is simulated.** "Maya" is a fictional non-technical studio owner. I (an AI) played her, answering the agents' questions as a real owner might — including two changes of mind that alter scope. Everything the **agents** produced is real, unedited output.
- **The agents were real and separate.** Each role ran as its own agent with fresh context, reading its generated role file (`project/.claude/agents/<role>.md`). Reviewers did not see the builders' reasoning, and they ran the tests and probed the app for themselves.
- **No GitHub here.** The collaboration used the file-based surface of the protocol (`.autocraft/work/<task>/handoff-N.md` and `review-N.md`) and local branches instead of pull requests. With GitHub, the same exchanges happen as PR comments and labels.
- **Status: release-ready for merge; go-live gated by T8.** All of T1–T7 and the hardening round H1 are built, independently reviewed and merged; **539 tests pass**. Deployment (T8) is intentionally blocked on Maya signing up for a host. Details in [What is left](#what-is-left). The finishing round was also a **token-efficiency exercise**: see [Token budget](#token-budget-lean-mode).

## Results at a glance

| | |
|---|---|
| What was built | A web app: visitors see the class schedule; students sign up, book, cancel; Maya adds, edits and cancels classes and sees who is booked; confirmation emails are recorded |
| Code / tests | ≈2,360 lines of application code, ≈2,880 lines of tests; **539 tests pass** on the merged app (344 from the build tasks + 177 QA tests + 18 regression tests for the defects found + new security tests) |
| Documents | spec, architecture, API contract, threat model, **5 decision records (ADRs)**, task list, 2 architecture reviews, 15 task handoff/review files, QA summary + traceability matrix, security audit |
| Agent runs | **26** (tracked in [`agent-runs.csv`](agent-runs.csv)); ≈**2.2 million tokens**; ≈**104 agent-minutes** (less wall-clock time: three builders and three reviewers ran in parallel) |
| Review rounds | architecture: 2 (6 MAJOR findings in round 1, approved round 2); tasks: 5 of 6 approved first time, 1 needed a fix round |
| Things reviewers caught that builders missed | 21 architecture findings; a major test gap in the roster; a crash on huge IDs; a contrast failure; weak email tests; and — only after merging — a clash between two correct branches |
| The owner's effort | ≈11 touchpoints, each seconds to a few minutes (listed [below](#everything-the-owner-did)) |

## The team

Maya chose the **lean `starter` team and added four roles**:

| Role | Why it was there |
|---|---|
| `requirements-analyst` | Turn the idea into a testable spec |
| `architect` ⇄ `principal-engineer` | Money is not involved, but personal data and double-booking are: worth a design debate |
| `developer` (several at once) | Build tasks with tests |
| `pr-reviewer` | Independent review of every task |
| `qa-engineer` | An independent tester who did not write the code |
| `security-auditor` | Scans and attack-minded review |
| `release-gatekeeper` | Final check before release *(not yet run — see below)* |

Notice that it began lean and grew *only where a real need existed*.

---

## Step 1 — Describe the idea, get a recommendation

**Owner types** (in the terminal; the same works as `/discover` inside an AI tool):

```bash
python3 ~/autocraft/bin/autocraft recommend "I run a small yoga studio. Students should be able to see our classes, book a spot, and cancel. Classes have limited spots. I want to add classes myself. Payments can come later."
```

**What it prints** ([full text](transcript-01-recommend.txt)):

```
  * fullstack-app: "I want an app people sign in to and use in the browser, that remembers their stuff."
  Also likely needed: authentication, database
  LEAN team  -> starter ...
  FULL team  -> web-product ...
```

> **A bug the example found:** the first time I ran this, the recommender replied *"I couldn't tell the kind of software from that"* — its keyword list didn't know words like "book", "students" or "classes". It failed gracefully (it fell back to the lean team and told the owner to run `/discover`), but it was a real defect in the product, fixed during this example.

## Step 2 — Choose and install the team

**Owner types:**

```bash
mkdir classbook && cd classbook && git init
python3 ~/autocraft/bin/autocraft init . --tool claude-code --team starter \
  --archetype fullstack-app --capability authentication,database,email-and-notifications \
  --add-role architect,principal-engineer,qa-engineer,release-gatekeeper --experience beginner
python3 .autocraft/framework/bin/autocraft doctor
```

**What you see** ([transcript](transcript-02-init.txt)): the 8 roles and 9 workflows installed, "doctor: OK". New folders appear: [`.claude/agents/`](project/.claude/agents/) (one file per role), [`.claude/skills/`](project/.claude/skills/) (the `/commands`), [`CLAUDE.md`](project/CLAUDE.md) (team guide), `.autocraft/config.yml`.

> **Another thing found:** `starter` originally had no `/start` command, and roles you *add* didn't switch on their matching workflows (`/design-architecture`, `/release-check`). Both fixed: workflows now adapt to the roles actually installed.

## Step 3 — The spec (`/start`)

**Agent:** the `requirements-analyst` writes [`docs/specs/classbook.md`](project/docs/specs/classbook.md): 6 user stories, ~25 testable Given/When/Then criteria, an **out-of-scope list** (payments, waitlists, recurring classes, social login…), non-functional needs, and **7 numbered questions with defaults**. It also noticed that "I want to add classes myself" implies an *admin* and flagged the personal-data risk for later roles.

**Owner answers** (simulated, in her own words):

| Q | Maya's answer | Effect |
|---|---|---|
| Q2 cancel cut-off | "Two hours is too tight. Students must cancel at least **12 hours** before, otherwise I lose the spot." | default changed |
| Q4 emails | "Yes please — a **confirmation email** when someone books, and one when they cancel." | **scope added** (new user story) |
| Q7 booking horizon | "No more than **30 days** ahead." | new rule |
| others | "Yes, default" | accepted |

**Agent:** updates the spec to *AGREED*, and — good practice — notes that there is **no email service yet**, so phase 1 uses a replaceable "mailer" that only records messages. A failed email must **never** undo a booking.

> **What the owner did:** read a 5-line summary and answered all 7 questions — 3 with changes, 4 with "yes, default" (≈3 minutes).

## Step 4 — The plan: architect ⇄ principal engineer (`/design-architecture`)

**Round 1.** The `architect` produced [architecture](project/docs/architecture/architecture.md), [API contract](project/docs/architecture/api.md), [threat model](project/docs/architecture/threat-model.md), [5 ADRs](project/docs/adr/) (each with a rejected alternative) and an [8-task work breakdown](project/docs/architecture/work-breakdown.md) — plus a plain-language summary for Maya. Key design: one small web app, SQLite with write-locking so "the database is the referee" for the last spot, spots-left *derived* (never stored).

The `principal-engineer` — a separate agent that did not write it — replied **CHANGES REQUESTED** with [21 findings](project/docs/architecture/reviews/review-1.md). Real examples:

- **[MAJOR] F1** — *"AC-2.3 is not met by the API design. Booking is POST-only and there is no class page… after login the browser does a GET of a POST-only URL and returns 405."* (the spec's "sign in, then return to the class" would have broken)
- **[MAJOR] F2** — CSRF protection depended on a session that doesn't exist yet at sign-in.
- **[MAJOR] F3** — nothing stopped a stray second admin; a changed admin email would leave the old one behind.
- **[MAJOR] F4** — the login lock-out would, behind the hosting proxy, treat *every user as one person* — one wrong-password burst could lock **Maya** out.
- **[MAJOR] F5/F6** — the three "parallel" tasks weren't really independent; and deployment was left to the very end although it was the riskiest assumption.
- Two **human decisions** for Maya (F19 hosting budget; F20 admin without two-step login). Plus a question that turned into a scope change (F21).

**Owner answers** (simulated): "Up to £10/month; pick the simplest host and tell me what to sign up for." · "Fine for now — my nephew Tom can reset my password by hand." · "Yes, show **next month's** classes greyed out with *'Opens for booking on <date>'* — students always ask."

**Round 2.** The architect answered **every** finding (accepted/changed or rejected with reasoning), restructured the task list (shared "kernel" first so later tasks are truly independent), chose a host, and recorded Tom's password reset as a *named accepted risk*. The principal engineer **re-verified each of the 21 findings in the documents themselves** and wrote [review-2: APPROVED](project/docs/architecture/reviews/review-2.md) — with 6 new minor items, folded into tasks.

**Parallel work:** while the principal re-reviewed the architecture, the requirements-analyst updated the **spec** for the scope change — two agents on two independent files at once.

> **Owner's gate:** read the plain-language summary, approved the architecture ("Looks good. I understand I need to sign up for Render later…") — recorded in [`status.md`](project/docs/architecture/status.md). ≈5 minutes.

## Step 5 — Build, one task at a time at first (`/build-feature`)

**T1 — skeleton + shared kernel.** The `developer` agent built it in its own git worktree: config that fails fast without leaking secrets, the time rules (exactly-12-hours, day-30 boundary, daylight-saving gaps), the database with the single-admin rule enforced *in the schema*, migrations, health endpoint, Dockerfile, CI file — **84 tests**. It reported what it could *not* verify (no Docker or CI here, pinned versions unconfirmed).
The `pr-reviewer` then ran the tests itself, started a real server, tried bad config, probed daylight-saving edges and wrote [review-1: APPROVED](project/.autocraft/work/T1/review-1.md) with 6 minor follow-ups.

**T2 — web shell** (CSRF without a session, security headers, size limits, safe redirects). 162 tests. Reviewer probed with real HTTP, even *removed* the CSRF helper from a template copy to prove the safety-net test fails — [APPROVED](project/.autocraft/work/T2/review-1.md).

**Owner merges** each approved task (the one thing agents never do).

## Step 6 — Three builders in parallel

With the kernel and shell merged, the three independent tasks ran **at the same time**, each developer in its own copy of the project:

| Task | Builder produced | Tests | Review result |
|---|---|---|---|
| **T3** accounts & sessions | sign-up/sign-in, safe password hashing, session handling, login throttling, admin bootstrap | 214 | **Approved** — reviewer started a live server and tried session fixation, wrong-password vs unknown-email timing (52 vs 50 ms), open redirects |
| **T4** schedule & admin | public schedule, class page, admin add/edit/cancel, roster | 212 | **Changes requested** (see below) |
| **T5** booking & cancellation | book, cancel, "my bookings", 20-actions/hour cap | 197 | **Approved** — reviewer made **9 deliberate breakages** (e.g. replaced the database lock with a plain one); *every one was caught by the tests* |

Three builders took ≈6 minutes of wall-clock (≈14 if done one after another); three reviewers ran in parallel too.

**T4's review** found a real gap, quoted:
> **[MAJOR] M-1** — *the roster's "booked only" filter is untested. Removing it, so cancelled students show as booked, leaves every test green… a coverage gap on AC-6.1.*
> plus: a huge class ID crashed with a 500 instead of 404 · greyed text failed the readability (contrast) standard · cancelling a class that already started was silently allowed.

The developer fixed all of it (and proved its new test works by breaking the filter and watching the test fail); the owner decided *"refuse cancelling a class that already started"*; the reviewer re-checked each point individually → **[APPROVED round 2](project/.autocraft/work/T4/review-2.md)**.

### The surprise only integration reveals

After merging T3 and T5 — both approved, both green on their own — the combined suite showed **12 errors**: `UNIQUE constraint failed: users.role`. T3 creates the single allowed admin at startup; T5's *test fixtures* inserted their own admin. Nothing in the app was wrong; the tests collided. A developer fixed the fixtures in a small separate change (the owner checked the 16-line diff and merged), and **the full suite went green: 249 passed**. The lesson, in the guide: *merge approved work early and run everything together.*

## Step 7 — Emails (T6)

The `developer` built the confirmation emails: sent **after** the booking is saved (so a mail problem can't undo it), de-duplicated, and — deliberately — **without the student's name in the body** (an attacker could choose a name). The reviewer's mutation probes: 10 deliberate breakages, 7 caught immediately; 2 harmless today; **2 exposed test gaps** (nothing proved the email is sent *after* the response; nothing pinned "no name in the body"). Approved, with those two tests handed to QA. Merged: **344 tests pass.**

## Step 8 — QA: an independent tester (T7)

The `qa-engineer` — who wrote none of the code — worked from the spec's acceptance criteria. In ≈25 minutes (the most expensive step: ≈321k tokens) it produced:

- a **test plan** and a **traceability matrix** mapping all 34 acceptance criteria to named tests ("no AC without a real test"),
- an **authorization matrix**: every one of 18 routes × {visitor, student, other student, admin} = 72 cases,
- **real-server race tests**: 50 simultaneous bookings for 1 spot → exactly 1 booking and 49 "Class is full"; 30 on 10 spots → exactly 10; p95 response 0.36 s (spec: under 1 s),
- a full **journey test** over real HTTP, accessibility checks over 25 page states, exploratory testing (odd Unicode, back button, expired sessions, clock edges),
- **21 deliberate code mutations, all caught**,
- and **9 minor defects**, each reproduced as a failing test marked "known defect" — e.g. `D-1` huge IDs still crash on the *booking* routes (T4's fix had only covered class pages), `D-3` the health URL rejects `HEAD` requests (an uptime monitor would think the studio is down), `D-5` error pages look tiny on a phone, `D-7` the admin page promised a "failed sign-ins" count that was never shown.

Result: **521 passed + 14 known-defect tests** on the QA branch. Read [`docs/qa/qa-summary.md`](project/docs/qa/qa-summary.md) — it starts with "What this means for you (Maya)" in plain words.

## Step 9 — Security audit

In parallel with QA, the `security-auditor` ran real scanners and a hostile read-through: dependency scan **clean**; code scan: 4 hits, all false positives (checked by hand); **no secrets** in the code or all 54 commits; every threat in the threat model checked against the code. Its [report](project/docs/security/audit-2026-10-10.md): **0 critical, 0 high, 3 medium, 7 low**. The most interesting:

- **Medium:** *every throttled sign-up attempt is still written to the database* — an anonymous attacker could fill the disk (61 requests left 61 rows in its probe).
- **Medium:** backups promised in the threat model don't exist yet (planned for T8) — "don't go live until closed."
- **Medium (deployment-dependent):** if the hosting proxy setting is wrong, everyone shares one IP and 20 failed logins lock out *everyone, including Maya* — to be verified on the first deploy.
- It confirmed that it **could not** find a way to bypass CSRF, steal a session, become admin, or read another student's data.

---

## What is left

| Item | Why it isn't done | Next step |
|---|---|---|
| ~~Hardening round H1~~ | **Done** with `token_mode: lean`: 1 developer run fixed D-1…D-9, the disk-fill risk, CSP/HSTS, retention and umask; every known-defect test became a regression test | — |
| ~~Review of the QA work + fixes~~ | **Done**: one combined independent review, probed the risky fixes, APPROVE with 2 minor follow-ups (applied) | — |
| ~~Release check~~ | **Done**: *release-ready for merge*; dependency scan clean, code scan unchanged (4 known false positives), no secrets | — |
| **T8 — hosting, backups, runbook** | **Blocked on a human**: Maya must sign up for the host (steps are in [ADR-0005](project/docs/adr/0005-single-instance-hosting-with-volume-and-backups.md)) | After sign-up: first deploy, backup/restore rehearsal, uptime monitor |
| Decision D-8 (spots left on greyed rows) | — | **Decided**: Maya said leave it out; the spec was amended |
| Still deferred (security) | Backups (M-1), proxy-hop check (M-3), scrypt upgrade (L-2), supply-chain pins (L-4/L-6) | Part of T8 / first deploy. Also confirm with Maya: sent-email records are purged after 90 days |

These are in [`project/docs/STATUS.md`](project/docs/STATUS.md) — that file is how any future session (or person) would pick up exactly here with `/status`.

## Token budget (lean mode)

A stated non-functional goal for the finishing round: **get to release-ready with limited tokens, without dropping any quality gate** (tests with every fix, independent review, human merge). The project was switched to `token_mode: lean` (see [protocol section 15](../../docs/protocol.md)).

| | Without a budget (build phase, T1–T7) | Finishing round with lean mode (H1 + review + release check) |
|---|---|---|
| Agent runs | 24 | **2** (+ the lead's own checks) |
| Tokens | ≈2.0 million | **≈190 thousand** (developer 107k, reviewer 81k) vs a planned cap of 450k |
| Work done | 6 tasks + QA + audit | 9 defects + 4 security items fixed, ~18 regression tests, review, release check |

What made the difference, in order of effect:
1. **A precise brief instead of exploration.** The developer got one file (`.autocraft/work/H1/brief.md`) listing each defect, the expected behaviour, and what *not* to touch; it read only the files it edited (21 tool calls).
2. **Defects were already failing tests**, so "done" was mechanical (suite green) rather than argued.
3. **One combined reviewer** instead of a review per fix, with *risk-tiered depth*: full probing only where the failure would hurt (sign-up flood, odd IDs, the admin count, headers); diff-and-tests for the rest. It still found a test that could never fail.
4. **Scanners run by the lead for free** (dependency, code, secret scans cost no model tokens).
5. **The release check was a short checklist over the evidence already in git**, not another agent exploring the code.
6. **Short reports** (the agents were limited to 10–30 lines) kept the lead's own context small.

Honest limits: the finishing round is cheaper partly because the earlier phase had already produced the specs, tests and QA matrix; lean mode cannot create that foundation for free. The release check here was run by the lead from the evidence pack rather than by a separate `release-gatekeeper` agent, which saves tokens but is less independent; for a real product, use the gatekeeper.

## Everything the owner did

| # | Moment | What | Time |
|---|---|---|---|
| 1 | Idea | Wrote two sentences | 1 min |
| 2 | Team | Chose lean + 4 roles | 2 min |
| 3 | Spec | Answered all 7 questions (3 changed, 4 "default") | 3 min |
| 4 | Plan | Answered 3 questions from the principal engineer (budget, admin protection, next-month view) | 3 min |
| 5 | Plan gate | Read the summary; approved | 5 min |
| 6–11 | Each task | Merged after review (T1, T2, T3, T5, T4, T6); decided one rule (started classes can't be cancelled); checked one 16-line fix | ≈1–2 min each |
| 12 | QA/security | Read two plain-language summaries; decided D-8 | 5 min |

Total owner effort ≈ 30–40 minutes (an estimate — the owner was simulated) for a working, reviewed, tested booking app with 26 agent runs behind it. **You never had to say which database, framework or test library to use.**

## What went wrong, and what we changed because of it

An example that only shows successes isn't trustworthy. In running this one we found, and fixed or recorded:

1. **The recommender missed the flagship example** (keywords) → fixed.
2. **The lean team had no `/start`; added roles didn't enable their workflows** → fixed (`needs:` in workflows).
3. **The architect over-built for a 1,000-student studio** (a security-heavy design with hand-written sessions, a throttling table, a backup design, a hosting ADR). The principal engineer judged it *sound*, not *proportionate*. A real owner can say *"simpler, please"* at the plan gate — **the guide should say so** (added to page 3).
4. **Two correct branches broke when merged.** Merge early; run everything together.
5. **A fix made in one place wasn't applied to its twin** (huge IDs fixed on class pages, still crashing on booking routes) — found only by QA and the security auditor. Independent roles looking at the *whole* app pay for themselves.
6. **Agents ran into the session's usage limit** — long multi-agent runs consume a lot (this one: ≈2M tokens). The guide now says start lean and expect QA to be the biggest single cost.
7. **A papercut:** the project's `pytest.ini` had `-q` which made the test summary line vanish — a reminder that agents' "all green" claims should be re-run, which the reviewers did.

## Run it yourself

```bash
cd examples/classbook/project
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest -o addopts=""                     # 539 tests pass
cp .env.example .env                     # then edit ADMIN_PASSWORD (14+ characters)
set -a; . ./.env; set +a
uvicorn --factory classbook.app:create_app --port 8000 --workers 1
# open http://localhost:8000   (admin sign-in: ADMIN_EMAIL / ADMIN_PASSWORD; emails are recorded, not sent)
```
(Verified: the app starts, `/health` answers `{"status":"ok"}`, the schedule page and security headers respond.)

## Where to look in `project/`

| Folder | What it is |
|---|---|
| `docs/specs/` | the agreed spec (with change log) |
| `docs/architecture/`, `docs/adr/` | the plan, the contract, the threat model, the decisions, **both reviews** |
| `.autocraft/work/T1…T6/` | every handoff and review between builders and reviewers |
| `docs/qa/`, `docs/security/` | QA summary, test plan, traceability; security audit |
| `docs/STATUS.md` | the live status board |
| `classbook/`, `tests/` | the application and its tests |
| `.claude/agents/`, `CLAUDE.md` | the generated team (what `autocraft init` created) |

*The vendored framework copy (`.autocraft/framework/`) and the QA branch's test files are not included here; regenerate the first with `autocraft sync`.*
