# 5. Choosing and customizing your team

## Start lean, grow when you feel the need

| Team | Roles | Pick it when |
|---|---|---|
| **starter** (lean) | planner · builder · reviewer · security checker | anything small or unclear; your first project |
| **web-product** | + designer · architect · principal engineer · front-end + back-end builders · QA · release checker · coordinator | websites, web apps, SaaS, internal tools |
| **api-backend** | architect · principal · back-end builder · QA · reviewer · security · release checker | APIs, scheduled jobs, queues, automation |
| **mobile** | + mobile builder · designer · device-aware QA · store-aware release checker | iPhone/Android apps |
| **ai-product** | + AI engineer · evaluation-first QA · injection red-team | chatbots, assistants, "ask my documents" |
| **data-ml** | data engineer · ML engineer · data-quality QA | pipelines, analytics, prediction models |
| **platform** | DevOps engineer · plan-first review | cloud infrastructure |
| **toolsmith** | + technical writer · compatibility gates | libraries, command-line tools, plugins, desktop apps |
| **makers** | game or embedded builder · playtest / update gates | games, devices |

List everything: `autocraft list teams`, `autocraft list roles`.

## When to add a role

| Symptom | Add |
|---|---|
| "The screens feel confusing or inconsistent" | `ux-designer` |
| "Bugs keep reaching me" | `qa-engineer` |
| "We keep changing the design halfway" | `architect` + `principal-engineer` |
| "I'm worried about security / personal data" | `security-auditor` (already in starter) + `privacy-compliance` capability |
| "I can't tell if it's safe to release" | `release-gatekeeper` |
| "Nobody can run it but the builder" | `technical-writer` |

## Software types and needs (profiles)

The team uses two kinds of knowledge about your project. You rarely pick them by hand — `/discover` does — but you can see and change them in `.autocraft/config.yml`.

- **Archetypes — what you're building** (20): static website, web app, full-stack app, mobile app, desktop app, game, internal tool, chat bot, plugin/extension, API, real-time service, event processor, scheduled job, script, data pipeline, AI assistant, ML service, library/CLI, infrastructure, embedded device. See the [catalog and "recipes"](../../archetypes/README.md) ("an online store = full-stack app + payments + email…").
- **Capabilities — things most products need** (10): login, payments, database, email/notifications, file uploads, search, monitoring, secrets, hosting, privacy. See [capabilities](../../capabilities/README.md).

## Changing the team

Run these in your project folder (replace the path if your copy of autocraft is elsewhere):

```bash
python3 ~/autocraft/bin/autocraft add-role qa-engineer
python3 ~/autocraft/bin/autocraft remove-role ux-designer
python3 ~/autocraft/bin/autocraft add-tool cursor          # same team, another AI tool
python3 ~/autocraft/bin/autocraft doctor                   # health check
```
Or, in your AI tool: `/customize-team` and say what you want in words.

## Your own rules

Put rules in plain English in `.autocraft/custom/team-rules.md`; every agent follows them.
```
Use British spelling in everything user-facing.
Never add a new dependency without asking me first.
Our brand colour is #1F6F5C.
```
For one role only: `.autocraft/custom/roles/<role>.append.md`, e.g. `reviewer: always check that error messages are kind and plain.`
After editing, run `autocraft sync` (or ask `/customize-team`) to apply it everywhere.

## Create a brand-new role

```bash
python3 ~/autocraft/bin/autocraft new-role accessibility-champion
# edit .autocraft/custom/roles/accessibility-champion.md  (mission, checklist, rules)
python3 ~/autocraft/bin/autocraft add-role accessibility-champion
```

## How hands-on do you want to be?

In `.autocraft/config.yml`:

| Setting | Meaning |
|---|---|
| `autonomy_level: 1` | you approve after every phase (best for learning) |
| `autonomy_level: 2` | you approve the plan and every merge (default) |
| `autonomy_level: 3` | you approve only merges/releases |
| `max_review_rounds: 3` | builder/reviewer rounds before they ask you |
| `max_parallel_developers: 3` | builders working at once |
| `experience: beginner / intermediate / expert` | how much the agents explain |

**The fixed points** (can't be switched off): independent review, tests with every change, no secrets in code, **humans merge**. `autocraft doctor` warns you if your team has no reviewer or no builder.

**Engineer?** Page 6 covers defining your own team file, per-role models (`--role-model`), replacing roles, custom workflows and keeping generated files in sync from CI.

**Next:** [6. For software engineers →](6-for-software-engineers.md) · or [7. FAQ and troubleshooting →](7-faq-and-troubleshooting.md)
