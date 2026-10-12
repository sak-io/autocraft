# Worked example: an Order Management API (think "Amazon-style ordering")

Goal: *"An API to create and manage customer orders for a retail site."*

## 0. Kickoff
```
$ python3 autocraft/bin/autocraft recommend "an API to create and manage customer orders for a retail site"
  -> api-service · team: api-backend (lean: starter)
$ python3 autocraft/bin/autocraft init ~/code/orders --tool claude-code --team api-backend --archetype api-service --capability authentication,database,payments --lang python
$ cd ~/code/orders && claude
> /start
```
(`--lang python` also adds the optional GitHub module: CI, scanning, templates.) Answers: payments are handled by a third party; personal data yes → sensitive: *personal*; autonomy **L2**.

## 1. Spec (requirements-analyst)
`docs/specs/orders.md` — actors: Customer, Admin, Payment provider. Stories: place order, view order, cancel order, list my orders, admin updates fulfilment status. Acceptance criteria, e.g.
*Given stock for item X is 1 · When two customers order X at once · Then exactly one succeeds and the other gets 409.*
Non-goals: catalog, search, shipping rates. Open question Q1: "Is partial fulfilment needed?" (default: no).

## 2. Architecture (architect ⇄ principal-engineer)
Architect proposes: modular monolith (FastAPI + PostgreSQL), outbox pattern for events, idempotency keys on `POST /orders`, JWT auth.
**Round 1 review (principal):**
- `[BLOCKER] F1` Overselling race: inventory decrement isn't atomic → use conditional `UPDATE … WHERE stock >= qty` or row locks.
- `[MAJOR] F2` No state-machine for order status; illegal transitions possible.
- `[MAJOR] F3` Threat model omits IDOR (customer reading another customer's order).
- `[MINOR] F4` Work item T4 too large; split.
Architect accepts all; adds ADR-0003 (optimistic stock reservation), state diagram, IDOR mitigations + test, splits T4. **Round 2:** `APPROVED`. You get a plain-language summary and approve.

## 3. Onboarding (repo-onboarder)
Confirms: create `you/orders` **private**; installs CI (`ruff`, `pytest`, `pip-audit`), CodeQL, Dependabot, secret scanning; protects `main` (PR + 1 review + `ci` check + no force push). Report: ✅ ×8, ⚠️ push protection unavailable on this plan → gitleaks added to CI.

## 4. Build (developer ⇄ pr-reviewer)
- **T1 Walking skeleton** → PR #1: `GET /health`, DB connection, 1 unit + 1 integration test. Reviewer: `[MINOR]` config hard-coded → fixed → `APPROVED`.
- **T2 Create order** → PR #2 (parallel with T3 *Authentication*, independent).
  - Reviewer round 1: `[BLOCKER]` handler trusts `customer_id` from request body (authz) · `[MAJOR]` no test for duplicate idempotency key.
  - Developer: fixes, adds both tests, replies `Fixed in 4f2a1c9`. Round 2: `VERDICT: APPROVED`, label `agent:approved`.

## 5. Pre-release (release-gatekeeper)
Finds: `[RELEASE-BLOCKER]` migration adds NOT NULL column without default (breaks rolling deploy) · no rollback note · CHANGELOG missing. Developer fixes; re-check all ✅ → label `agent:release-ready`, comment mentions you:

> **Release-ready.** Ships: create-order endpoint. Risk: medium (new write path). Rollback: revert PR; migration is reversible. Waiting for your approval and merge.

## 6. You
Open PR #2 → read → Approve → Squash and merge. 🎉

## 7. Ongoing
Monday: weekly scan runs; `/security-scan` triages 3 Dependabot alerts → 1 real HIGH issue filed → `/build-feature` fixes it through the same loop.

---
## Same project, bigger team: adding a mobile app
Later you want a phone app for these orders: `autocraft init . --team api-backend,mobile --archetype api-service,mobile-app` (it adds `ux-designer` and `mobile-developer`; nothing is lost). Differences you will see:
- **ux-designer** produces flows/wireframes first, including offline and permission-denied states.
- **architect** adds a mobile section (offline cache, secure token storage, **force-update path for old app versions**) and a `[contract]` task so the API's OpenAPI file lands before `[mobile]` and `[api]` work proceeds in parallel.
- **Reviewers** reject a mobile PR with no widget tests for the error state, or an API change that breaks the previous app version.
- **release-gatekeeper** adds store-review items and a staged-rollout plan; **you** submit to the stores.
