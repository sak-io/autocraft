---
name: discover
description: Turns a plain-language idea ("I want an app where…") into a recommended set of archetypes and capabilities, explained in simple words, then records the choice in .autocraft/config.yml. Use when the user is unsure what kind of software they need or doesn't know technical terms.
---

# /discover – "I have an idea, I don't know what it needs"

Assume the person has **never worked in software**. No jargon without a one-line explanation. Never make them choose a technology — you recommend, they confirm.

1. **Listen.** Ask: *"Describe what you want in your own words — who will use it, and what should it let them do?"* If they already did, don't ask again.
2. **Probe gently (max 4 questions, each with a default):**
   - Where will people use it — a website, a phone app, on their computer, inside Slack, or does nobody use it directly (it just runs)?
   - Do people need to sign in, or pay, or upload things, or get emails/notifications?
   - Does it need to remember information (save things)? Is any of it personal, financial or health-related?
   - Do you already have anything (code, data, a design, a domain, a GitHub account)?
3. **Map it.** Read `archetypes/README.md` (or `.autocraft/archetypes/`) — the recipes table and each profile's *In plain words* — and `capabilities/` *Trigger words*. Choose the **smallest set** that covers the idea. Prefer fewer components for a first version.
4. **Explain back in plain language**, like this:
   > Here's what I think you're building: **<one sentence>**.
   > It's made of: **<archetype>** — *<its "In plain words" line>*; **<archetype>** — …
   > It will also need: **<capability>** (*<why, in one line>*) …
   > I'd skip for now: **<things you can add later>**.
   > Roughly how big: **<small / medium / large>**, built as **<N>** small steps you can approve one by one.
5. **Flag human decisions**, calmly: money (payments), law/privacy (children, health, EU users), accounts you must create (Apple/Google developer, domain, cloud), anything safety-related.
6. **Confirm**, then write `.autocraft/config.yml`: `archetypes`, `capabilities` (always include `secrets-and-config`, `deployment-hosting`, `analytics-observability`), `experience` (default `beginner`), and suggested `language`. Offer to continue with `/start` (spec → architecture → …).

Never recommend more than needed. If unsure between two options, pick the simpler and say what would make you switch.
