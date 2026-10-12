# Spec: Pantry Pal (version 1)

**Status:** DRAFT  ·  **Owner:** (owner)  ·  **Date:** 2026-10-12  ·  **Author:** requirements-analyst (ingest mode)
**Sources:** [concept] = `docs/product-concept.md`, [plan] = `docs/technical-plan.md`. Neither was edited. `ASSUMPTION` = the documents are silent; the default is mine and needs the owner's OK. Gaps are in section 7 (G1..G22).

## 1. Problem & goal
Households waste food and money because nobody knows what is at home or what to buy [concept §Vision]. Pantry Pal gives a household (2-6 people who share shopping, mostly on phones, often with weak signal [concept §Who it is for]) one shared grocery list and pantry. **Goal of v1:** shopping is faster and less food is thrown away. **Success:** a household adds 20 pantry items in week 1 and still uses the list after a month [concept §Success]. This spec covers v1 only.

## 2. Actors
- **Member**: a signed-in person in one household; does everything in v1.
- **Household creator**: the first member [plan §Accounts]. Whether they have extra powers is undecided (G8).
- **Invitee**: someone with an invite link, not yet a member.
- **External services** (not people): email provider (ASSUMPTION), OpenFoodFacts, Claude API, push service [plan].

## 3. User stories & acceptance criteria
(Plain words: a *household* is the group sharing one list and pantry. A *magic link* is a one-time sign-in link emailed to you instead of a password.)

### US-1 Sign in without a password
As a visitor I want to sign in with a link sent to my email so that I need no password. [plan §Accounts]
- AC-1.1 **Given** a valid email **When** I request sign-in **Then** one email with a sign-in link is sent within 60 s (ASSUMPTION on 60 s, G9). [plan §Accounts]
- AC-1.2 **Given** a link **When** I open it the first time before expiry **Then** I am signed in; **When** I open it again or after expiry (default 15 min) **Then** it is rejected. [plan §Accounts; capability authentication "Must test"]
- AC-1.3 **Given** I am signed out **When** I request any household data via the API **Then** I get 401 and no data. ASSUMPTION (authentication capability)
- AC-1.4 **Given** an unknown versus known email **When** I request sign-in **Then** the response is identical (no account-existence leak) and requests are rate limited (default 5/hour/email). ASSUMPTION (authentication capability)

### US-2 Create and join a household
As a new user I want to create a household or join one by invite link so that we share data. [plan §Accounts; concept §Core 1]
- AC-2.1 **Given** I am signed in with no household **When** I create one **Then** I become its member and the first member. [plan §Accounts]
- AC-2.2 **Given** a member **When** they generate an invite link **Then** a signed-in invitee opening it joins that household and sees its list. [plan §Accounts]
- AC-2.3 **Given** an expired, revoked or already-used invite (defaults: 7 days, single use) **When** opened **Then** joining is refused with a clear message. ASSUMPTION (G8)
- AC-2.4 **Given** a household with 6 members **When** a 7th joins **Then** refused (default hard cap 6). [concept §Who it is for] ASSUMPTION on enforcing (G8)

### US-3 Shared grocery list
As a member I want to add, tick off and remove items on a shared list so that everyone knows what to buy. [concept §Core 1]
- AC-3.1 **Given** a list **When** I add, tick, untick or remove an item **Then** it persists and survives reload. [concept §Core 1]
- AC-3.2 **Given** member A changed the list **When** member B has the list open and visible **Then** B sees the change within 30 s (+ one poll interval of tolerance, so at most 35 s) without reloading. [concept §Core 1 "quickly"; plan §Shared list freshness; G2]
- AC-3.3 **Given** A and B tick the same item at about the same time **Then** it ends ticked once and no error is shown. ASSUMPTION (G14)
- AC-3.4 **Given** a list with 500 items **When** loaded **Then** it renders in under 2 s on a mid-range phone on 4G (ASSUMPTION, G15).

### US-4 Use the list offline in the store
As a shopper with no signal I want to tick and add items and have them sync later. [concept §Core 6, §Who it is for]
- AC-4.1 **Given** the list was loaded earlier **When** the connection drops and I reopen the app **Then** the list still opens (needs a cached app shell, G1). [concept §Core 6]
- AC-4.2 **Given** offline **When** I add, tick or remove items **Then** the UI updates at once and shows "not synced yet". [concept §Core 6]
- AC-4.3 **Given** queued offline changes **When** the connection returns **Then** they upload within 30 s, the indicator clears, and nothing is lost or duplicated, even after an app restart while offline. [concept §Core 6]
- AC-4.4 **Given** offline edits conflict with another member's online edits **Then** the documented rule (default: last write wins per item; removal beats tick) is applied and both people end with the same list. ASSUMPTION (G1, G14)
- AC-4.5 **Given** my sign-in expired while offline **When** I reconnect **Then** queued changes are kept, I re-authenticate, and they are then synced. ASSUMPTION (G1)

### US-5 Pantry inventory with expiry
As a member I want to record what is at home with quantity and expiry so that I can use food before it spoils. [concept §Core 2]
- AC-5.1 **Given** I add an item with name, quantity and optional expiry date **Then** all members see it. [concept §Core 2; G13 for units and optional expiry]
- AC-5.2 **Given** items with expiry **When** the pantry is shown **Then** items expired or expiring within 3 days (default) are visually highlighted, soonest first, and the highlight is not by colour alone. [concept §Core 2 "nearing expiry" undefined, G13; accessibility ASSUMPTION]
- AC-5.3 **Given** I buy a ticked list item **When** I choose "move to pantry" **Then** it is added to the pantry with the name prefilled. ASSUMPTION: the link between list and pantry is implied but never described (G13)
- AC-5.4 **Given** a free household **When** it exceeds the free item limit **Then** it is told clearly and nothing is deleted. [concept §Plans] Limit is undefined (G7).

### US-6 Morning expiry reminder
As a member I want a morning notification such as "3 things expire in the next 2 days" so that I do not forget. [concept §Core 3; plan §Notifications]
- AC-6.1 **Given** I enabled notifications and my household has N>0 items expiring in the next 2 days **When** 08:00 household local time passes (default, G4) **Then** I get exactly one notification with the correct N. [concept §Core 3]
- AC-6.2 **Given** N=0 **Then** no notification is sent. ASSUMPTION
- AC-6.3 **Given** the scheduler runs twice or is retried **Then** no duplicate notification is sent. [capability email-and-notifications "Must test"]
- AC-6.4 **Given** I turned reminders off or never granted permission **Then** I am never notified, and I can change this in settings. ASSUMPTION (consent; G3)
- AC-6.5 **Given** the daily job fails or does not run **Then** an alert reaches the owner. [capability analytics-observability "Must test"]
- Delivery on real phones (iOS especially) cannot be proven by automated tests; see G3 for the manual check.

### US-7 Add by barcode
As a member I want to scan a product barcode so that I can add it quickly. [concept §Core 4; plan §Barcode]
- AC-7.1 **Given** camera permission and a known barcode **When** scanned **Then** the product name is prefilled in the add form for confirmation. [plan §Barcode]
- AC-7.2 **Given** an unknown code, lookup failure or timeout (default 5 s) **Then** I can add the item manually with the code kept; nothing blocks. ASSUMPTION (G5)
- AC-7.3 **Given** camera permission is denied or unsupported **Then** manual entry is offered. ASSUMPTION (G5)
- AC-7.4 Automated tests use fixed barcode images and a mocked OpenFoodFacts; real-camera behaviour is a manual check per supported browser (G5).

### US-8 "What can I cook?"
As a member I want meal suggestions from my pantry, soonest-expiring food first, so that I waste less. [concept §Core 5; plan §Meal suggestions]
- AC-8.1 **Given** a pantry with items **When** I ask **Then** I see at least 1 and up to 5 recipes (default) in a fixed structure (title, ingredients, steps). [plan §Meal suggestions; count ASSUMPTION]
- AC-8.2 **Given** items expiring soon **Then** the request ranks them first, verified by checking the *request* sent to the AI, not its (non-deterministic) answer. [concept §Core 5; G6]
- AC-8.3 **Given** the AI service fails, times out or returns malformed data **Then** a friendly error is shown and the app keeps working. ASSUMPTION
- AC-8.4 **Given** a request **Then** only item names and expiry dates are sent: no email, name, household id or other personal data. ASSUMPTION [concept §Principles; G6]
- AC-8.5 **Given** a household over its daily suggestion cap (default 10/day) **Then** it gets a polite refusal. ASSUMPTION (cost, G6/G15)

### US-9 Privacy: only my household sees my data
As a member I want my household's data visible only to its members and deletable by me. [concept §Principles; plan §Stack "row-level security"]
- AC-9.1 **Given** two households **When** a member of A requests B's list, pantry, members or suggestions by any API route or direct database access **Then** nothing is returned (tested with two real accounts against a real test database). [concept §Principles; archetype fullstack-app "Must test"]
- AC-9.2 **Given** a member **When** they request deletion of their account (or last member deletes the household) **Then** personal data is removed from the live database, with backups and third-party copies following a documented schedule. ASSUMPTION (privacy-compliance; G10)
- AC-9.3 **Given** logs, error reports and analytics **Then** they contain no emails, tokens or household contents. ASSUMPTION (capabilities)
- AC-9.4 **Given** "we never sell household data" **Then** a data map lists every third party that receives data (hosting, email, AI, push) and the privacy policy matches it. [concept §Principles; G6, G10]

### US-10 Owner can measure success
As the owner I want to know whether households reach 20 items in week 1 and are still active after a month. [concept §Success]
- AC-10.1 **Given** consent rules are met **When** a household adds its 20th pantry item within 7 days of creation **Then** a counted event (no item contents) is recorded. ASSUMPTION: no analytics in [plan] (G12)
- AC-10.2 **Given** "still uses the list" is defined (default: at least one list action in days 28-35) **Then** a report can compute it. (G12)

## 4. Non-goals (v1)
Taking payments or billing for Premium; any price [concept §Plans "to be decided"]; native iOS/Android apps (ASSUMPTION); real-time push updates/websockets [plan §Shared list]; multiple households per user; roles beyond member; shopping by store or price; recipes saved by users; dietary or allergy filters (G6); languages other than English; ads [concept §Principles]; household data export beyond account deletion (G10); admin back-office.

## 5. Non-functional needs
| Area | Need | Source |
|---|---|---|
| Load | ASSUMPTION: under 1,000 households (about 4,000 users) in year 1; polling at 30 s means up to ~11M requests/day if every user left the app open all day, so poll only while visible and use cheap "no change" responses | none; archetype default; G15 |
| Latency | ASSUMPTION: p95 API under 500 ms; list opens under 2 s on 4G | none |
| Availability | ASSUMPTION: best effort about 99.5%; daily backups with a restore tested once | none; G17 |
| Data sensitivity | Personal (email; household makeup; eating habits). No payments, no children's accounts (ASSUMPTION, G10) | concept, plan |
| Privacy/compliance | Visible only to members [concept §Principles]; GDPR-style deletion and consent assumed (EU users likely, G10) | |
| Security | Authorization enforced on the server and in the database for every route; invite and sign-in links single-use and expiring; secrets only on server (Claude, Supabase service key); prompt-injection safe use of user text in AI prompts (G6); rate limits on sign-in, barcode lookup, AI | capabilities |
| Cost | ASSUMPTION: budget alert on day one; Claude API and email volume capped per household (G15) | capability deployment-hosting |
| Compatibility | ASSUMPTION: current iOS Safari and Android Chrome, installable as a home-screen web app (needed for G1, G3) | |
| Accessibility | ASSUMPTION: keyboard and screen-reader usable, WCAG 2.1 AA target | archetype |
| Observability | Error tracking, health route, alert on missed daily job | capability |
| Testing | Unit, integration against a real test database, and one end-to-end flow in CI are required (see G11) | protocol, archetype |

## 6. Also needed (capabilities detected)
Already in config: database, authentication, email-and-notifications, privacy-compliance, plus always-on secrets-and-config, deployment-hosting, analytics-observability. **Candidate to add after owner confirms:** payments (trigger "Premium", "price"), deferred out of v1 by default (G7). Archetype questions answered from the documents: users = household members; accounts = email magic link; data = personal; notifications = yes; first-year users = not stated (default under 1,000).

## 7. Gaps, ambiguities and contradictions
Severity: **BLOCKER** = architecture cannot be designed correctly without an answer; **MAJOR** = would cause rework or risk; **MINOR** = safe to default.

| # | Sev | Where | Issue and why it matters | Recommended default |
|---|---|---|---|---|
| G1 | BLOCKER | concept §Core 6 vs plan §Stack/§Shared list | **Contradiction.** The concept requires offline use with later sync. The plan is server-rendered pages plus 30 s polling and says nothing about a cached app, local storage, a sync queue, conflict rules or sign-in expiry while offline. This is the hardest feature and is untestable without those. | Installable web app with a service worker caching the shell, list kept in browser storage, a queued change log replayed on reconnect with per-item last-write-wins; architect records an ADR. Offline scope limited to the list (pantry read-only offline). |
| G2 | MAJOR | concept §Core 1 "quickly" vs plan 30 s polling | "Quickly" is undefined; 30 s may feel slow to a shopper watching a partner tick items. | Accept 30 s worst case (AC-3.2), refresh immediately on app focus and after the user's own change. |
| G3 | BLOCKER | plan §Notifications vs concept §Core 3 | Plan says "push notification" but the product is a website. Web push on iPhone only works for apps added to the home screen (iOS 16.4+) and needs permission. No scheduler, time zone, delivery provider or fallback is named. Cannot be verified by automated tests alone. | Home-screen web app with web push, plus email fallback for users without push; scheduled job at 08:00 household time zone; manual device check per platform before release. |
| G4 | MAJOR | concept §Core 3 "morning", "next 2 days" | Time zone, send time, who gets it, per-user opt-out and the 2-day window versus the highlight window are undefined. | 08:00 household time zone, every opted-in member, 2 days (reminder) and 3 days (highlight) as configuration values. |
| G5 | MAJOR | plan §Barcode vs concept §Core 4 | Browser barcode scanning varies by browser (no built-in support in Safari); OpenFoodFacts does not know every product, has usage terms and attribution rules, and rate limits; camera needs HTTPS and permission; no fallback described. | Scanner library plus manual-entry fallback; cache lookups on the server; show OpenFoodFacts attribution; real-camera test is manual. |
| G6 | BLOCKER | plan §Meal suggestions vs concept §Principles | Pantry contents go to a third party (Claude API). Concept promises data is visible "only to its members"; this must be reconciled and disclosed. Also undefined: cost per call, who may call it (Premium?), allergy/dietary safety (a bad suggestion could harm), prompt-injection via item names, non-deterministic output so "good suggestion" is untestable. | Owner confirms sharing item names and expiry only (no personal data) is acceptable and states it in the privacy policy; hard daily cap; structured output validated; item text treated as data; no allergy claims, with a visible disclaimer. |
| G7 | MAJOR | concept §Plans vs plan (no billing) and concept §Core 5 | **Contradiction.** Meal suggestions are a core v1 feature but also a Premium feature; the plan has no payments, no entitlement or plan field, no price. "Small households" and "unlimited items" have no numbers. | v1 ships with no billing: suggestions available to all under the daily cap; a free item limit is configuration (default 100 pantry items) and not enforced hard until pricing is set; payments is a later phase. |
| G8 | MAJOR | plan §Accounts vs concept §Who it is for | Household rules undefined: invite expiry/revocation, cap of 6, can one person be in two households, leave/remove a member, who can revoke, what if the creator leaves, whether an invite link plus magic link works on first sign-in. An invite link is a credential. | Single household per user, cap 6, single-use 7-day invites revocable by any member, any member can leave, last member leaving deletes the household. |
| G9 | MAJOR | plan §Accounts | Magic links depend on email deliverability and no provider is chosen. On phones, links often open in the mail app's built-in browser, so the session lands in the wrong browser (hurts a home-screen web app). No expiry or rate limits stated. | Transactional email provider with SPF/DKIM/DMARC; 15 min single-use links; also accept a 6-digit code typed into the open app. |
| G10 | MAJOR | concept §Principles; none in plan | No privacy design: no data map, retention, export/deletion, policy, consent, region (EU data residency?), breach plan, or minimum age (parents imply children may be members). | Data map and policy before launch, account deletion in v1, EU region for database, minimum age 16 with no child accounts; owner seeks a legal check. |
| G11 | BLOCKER | plan §Testing "after the first release" vs protocol rule 2 and archetype | **Contradiction** with the team's non-negotiable rules and the owner's own quality needs: tests cannot be deferred. | Tests ship with each feature; CI with unit, integration (two-household isolation) and one E2E flow from day one. The plan line is superseded; owner to confirm. |
| G12 | MAJOR | concept §Success vs plan | Success is defined but not measurable: no analytics or error monitoring in the plan; "still uses the list" undefined; analytics needs consent and must not capture contents. | Privacy-friendly analytics with counted events only; "active" = at least one list action in days 28-35; hosted error tracker. |
| G13 | MAJOR | concept §Core 2 | Undefined: quantity unit (count, grams, "1 bag"), whether expiry is optional, "nearing expiry" window, what happens to expired items, categories, duplicates, and how a bought list item becomes a pantry item (implied, never described). | Free-text unit plus number, expiry optional, 3-day highlight, expired items stay until removed, "move to pantry" action (AC-5.3). |
| G14 | MAJOR | concept §Core 1/6 | Concurrent edits (two ticks, edit while another deletes, offline versus online) have no rule. | Per-item last-write-wins with timestamps from the server; removal beats tick; documented and tested. |
| G15 | MAJOR | none | No scale or cost numbers. Polling can multiply load; Vercel/Supabase free tiers have limits; Claude API and email are per-use costs. | Year-1 under 1,000 households; poll only when visible; monthly budget alerts on all four services; caps per household. Owner states a monthly budget. |
| G16 | MAJOR | plan §Stack | Two access paths to data: REST routes inside Next.js and row-level security in Supabase. If routes use the Supabase service key, row-level security is bypassed and one coding mistake leaks another household's data. | Routes act as the signed-in user so database rules always apply; service key only for the scheduler; every route tested with two households (AC-9.1). Architect to confirm in an ADR. |
| G17 | MINOR | none | Availability, backup and restore targets missing. | Best effort, daily backups, restore tested once (AC in NFRs). |
| G18 | MINOR | concept §Who it is for | "Mostly a phone": is a native app wanted later? Language, units, date format and time zone unspecified. | English, mobile-first responsive web app; native out of scope. |
| G19 | MINOR | concept §Principles | "Never sell data" is a promise with no test. | Covered by the data map and policy check (AC-9.4); no third-party trackers or ad SDKs. |
| G20 | MINOR | plan §Barcode/§Meal | The Claude API key and Supabase service key are server secrets; leaks cause bills and breaches. | Platform secret store only; separate keys per environment; rotation noted in runbook. |
| G21 | MINOR | concept §Core 3/5 | Terms used without definition: "household", "item", "meal", "Premium", "small households", "quickly", "nearing". | Defined in this spec; owner to correct. |
| G22 | MINOR | plan vs concept | Plan lists no admin or support tool, yet account/household deletion and abuse (invite spam) need handling. | Out of scope for v1; owner handles support by database admin console. |

### Questions that block progress (answer "default" or correct)
1. G1: Offline = list only, last-write-wins, installable web app? (default yes)
2. G3: Reminders by home-screen web push plus email fallback, 08:00 local? (default yes)
3. G6: OK to send pantry item names and expiry (no personal data) to Claude, disclosed in the privacy policy? (default yes)
4. G7: No billing in v1; meal suggestions free under a daily cap? (default yes)
5. G11: Tests and CI from day one, replacing "after first release"? (default yes)

Work continues on the defaults until you answer.

## 8. Handoff note
Next role is the architect. The architect should record ADRs for offline sync (G1), notifications (G3), data access path and row-level security (G16), and the AI call (G6).
