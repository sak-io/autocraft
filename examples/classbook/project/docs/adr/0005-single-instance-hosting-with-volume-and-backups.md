# ADR 0005: Host on Render as one small service with a persistent disk

- **Status:** Accepted (Maya, 2026-10-10: "simplest, up to 10 pounds a month")  ·  **Date:** 2026-10-10

## Context
SQLite needs a persistent local disk and a single writer (ADR-0002). Free tiers with disks are rare. Maya has no host and wants the simplest option, ceiling 10 GBP/month, with exact sign-up steps.

## Decision
Render (render.com): one **Web Service** running the Docker image, paid "Starter" size, with one **persistent disk of 1 GB** mounted at `/data` (`DATABASE_PATH=/data/classbook.db`). The disk limits it to one instance, which is what we want. ASSUMPTION to verify at sign-up in T8: about US$7/month for the service plus about US$0.25/month for the disk (roughly 6 GBP), HTTPS and custom domain included, point-and-click dashboard, daily disk snapshots kept about 7 days. If the real price exceeds 10 GBP, stop and ask Maya. A `render.yaml` in the repo describes the service so it is created with one click ("Blueprint").
Backups: in-app nightly `VACUUM INTO` copy on the disk (7 kept), host snapshots, and the admin "Download backup" link for a monthly copy Maya stores privately.
Alerting: a free external uptime monitor (e.g. UptimeRobot) pings `/health` and emails Maya.

**What Maya must do** (blocked on human: host sign-up; nothing else needs her):
1. Create an account at render.com using her email; add a payment card.
2. In Account settings, set a spending notification at 10 GBP, and invite Tom as a team member (so he can fix things).
3. Tom (or a developer) puts the code in a Git repository and, in Render, chooses New > Blueprint and selects it (this uses our `render.yaml`).
4. In the service's Environment page, Maya types her admin email and a long password (14+ characters) into `ADMIN_EMAIL` and `ADMIN_PASSWORD`. She does not share the password in chat or email.
5. Create a free uptime-monitor account pointing at `https://<her-address>/health` with alerts to her email.
6. Press Deploy when Tom says the release is ready. If she forgets her password: Tom edits `ADMIN_PASSWORD` there and redeploys.

## Alternatives considered
1. Fly.io - cheaper and flexible, but needs a command-line tool; not "simplest" for Maya.
2. Free tiers without a disk (serverless, free web services) - would lose the SQLite file on restart.
3. A cheap VPS - Maya/Tom would manage server patches and certificates; the capability says avoid.
4. Managed Postgres plus a free web tier - removes the disk need but adds a second service and a short free-trial limit; revisit if the studio outgrows this.

## Consequences
Short downtime on deploy is accepted. Prices and features are re-checked at sign-up. Moving host later means copying the one database file (the admin download also serves as an export).
