# ADR 0002: SQLite, derived spots-left, BEGIN IMMEDIATE for booking

- **Status:** Accepted  ·  **Date:** 2026-10-10

## Context
The database capability defaults to managed Postgres. Budget is near zero, load is small (~50 simultaneous bookers at peak), but correctness under concurrency is required (AC-3.3, "never negative").

## Decision
Use SQLite (WAL mode, `busy_timeout`, foreign keys on) in one app process. Spots left is computed (`capacity - booked count`), never stored. Any write depending on a count runs in `BEGIN IMMEDIATE`, so the check and the insert are atomic. A partial unique index forbids two active bookings of one student on one class. Migrations are numbered SQL files with a tiny runner. Fixed settings, identical in tests: WAL, `synchronous=FULL`, `foreign_keys=ON`, `busy_timeout=5000`; connections use autocommit mode with an explicit `BEGIN IMMEDIATE` helper (`kernel.db.write_tx`) so lock waits honour the timeout. WAL needs a local disk.

## Alternatives considered
1. Managed Postgres (`SELECT ... FOR UPDATE`) – best long-term, but free tiers expire/limit, add an external service, a secret and network failure modes; deferred until growth. Data access stays in services with plain SQL to keep this move cheap.
2. SQLite with a stored `spots_left` counter – two sources of truth that can drift; rejected for the spec's sync requirement.
3. In-process Python lock – breaks as soon as there are two workers/processes; the database must be the referee.

## Consequences
Exactly one writer process/machine; no zero-downtime deploy. Needs a persistent disk and backups. Must run uvicorn with one worker (documented, checked in T6).
