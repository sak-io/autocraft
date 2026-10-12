# T1 handoff 1: walking skeleton + shared kernel

Branch `feat/T1-skeleton-kernel` (from main). No GitHub: this file is the pull request (protocol s12).

## What and why
The foundation every later task imports (architecture s2/s3): nothing from T2-T8.
- `classbook/config.py`: env-only settings, validated at startup; problems name the variable, never the value; `ADMIN_PASSWORD` hidden from repr; `load_or_exit()` prints and exits 1.
- `classbook/kernel/timeutil.py`: `Clock`/`FixedClock` (whole seconds, UTC), stored text `YYYY-MM-DDTHH:MM:SSZ`, London<->UTC, gap rejected (`NonexistentLocalTime`), fold = first occurrence, admin-input parser.
- `classbook/kernel/rules.py`: `is_bookable` (active and now < start <= now+30x24h), `opens_at`, `is_listed` (60 days), `cancel_allowed` (start-now >= 12h), `SPOTS_LEFT_SQL` + `spots_left()`.
- `classbook/kernel/db.py`: `connect` (WAL, synchronous=FULL, foreign_keys=ON, busy_timeout=5000, autocommit), `write_tx()` (BEGIN IMMEDIATE, rollback on error, `DatabaseBusy` on timeout), `read_conn()`, `migrate()` (numbered SQL, one transaction each, `schema_version`, idempotent, additive, pre-migration `VACUUM INTO` copy when data exists, refuses a DB newer than the code).
- `classbook/migrations/0001_initial.sql`: full schema incl. one-admin partial index, active-booking partial index, `cancelled_by`, `messages`, `login_failures`, and `user_actions` (F24).
- `classbook/kernel/validators.py`: limits (name 80, email 254, title 100, instructor 80, capacity 1..200, duration 5..480, password 10..128, admin 14, body 16 KB constant) and `FieldError` (messages never echo input).
- `classbook/logging_setup.py` + `classbook/app.py`: JSON log lines with request id, `X-Request-ID` header, generic 500 page (logs exception type + stack locations only, no message/source/query string), `DatabaseBusy` -> 503, `GET /health` (503 `{"status":"unavailable"}` on DB failure), app factory migrates on start.
- `Dockerfile` (non-root, one uvicorn worker, healthcheck), `.github/workflows/ci.yml` (pytest, compileall, pip-audit, gitleaks, docker build+health), `.env.example`, `.gitignore`, `.dockerignore`, pinned `requirements*.txt`.

## How to verify
```
cd <worktree>
/tmp/claude-0/-home-user-autocraft/4dc487e6-d297-5355-ab6e-8239135c933c/scratchpad/venv/bin/python -m pytest
python -m compileall -q classbook tests
# run locally (fake values):
APP_ENV=development DATABASE_PATH=/tmp/c.db ADMIN_EMAIL=m@example.com ADMIN_PASSWORD=long-enough-password-1 \
  uvicorn --factory classbook.app:create_app --workers 1 &   # then: curl -i localhost:8000/health
ADMIN_EMAIL=m@example.com ADMIN_PASSWORD=short uvicorn --factory classbook.app:create_app   # exits 1, message names ADMIN_PASSWORD, no value
```
I ran the local start and the bad-config start by hand (health 200, JSON logs, exit with message).

## Test evidence
`84 passed, 1 warning in ~2s` (warning: starlette says httpx TestClient is deprecated in favour of `httpx2`; not installed, not needed).
Files: test_timeutil, test_rules (exactly 12h allowed / 12h-1s refused / +1s allowed; day 30 allowed / +1s refused / -1s allowed; 30x24h across autumn and spring DST changes; label appears at `opens_at`; 60-day horizon), test_validators, test_config, test_migrations (empty DB, idempotent, upgrade with backup, failed migration rolls back, newer DB refused, pragmas), test_constraints (capacity 0/-1, duplicate active booking, second admin, enums, FK, cascades), test_write_tx (waits ~1 s on a held lock and succeeds; times out with `DatabaseBusy`; 20 threads read-then-write with no lost updates; rollback), test_app (health, 503, 500 logging with request id and no secrets, fail-fast).

## Architecture deviations / choices (ambiguity resolved with the architecture's wording where it exists)
1. **Size**: the diff is ~1,600 lines (about 740 code/SQL, rest tests) against the "< 400 lines" guideline. T1's scope in the work breakdown is large; kept as one branch in 5 logical commits (config+validators, time+rules, db+schema, app+logging+Docker, CI). Reviewer may review per commit.
2. `tzdata==2025.2` added to `requirements.txt` (not installed in the dev venv, which uses the system zoneinfo) so `Europe/London` works in `python:3.13-slim`. Version is from memory: verify it installs. All requirement pins are the venv's versions; `pip-audit==2.9.0` pin in dev requirements is unverified (not installed here).
3. `write_tx(path)` takes a database path and yields its own connection (architecture says it "opens the connection"). `now` must be read inside it by the caller (`clock.now()`); the kernel does not force this.
4. Extra table `user_actions(id, user_id, at)` for F24 (architecture did not name it); sign-up throttle can reuse `login_failures` with an `ip:`-style key. `bookings` has `CHECK ((status='booked') = (cancelled_by IS NULL))`: stricter than the architecture; T4/T5 fixtures must set `cancelled_by` on cancelled rows. `classes.duration_min >= 1` check added (validator enforces 5..480). Email stored lowercase is enforced by CHECK.
5. Config: `ADMIN_EMAIL`/`ADMIN_PASSWORD` required in every environment (not just production); `APP_ENV` in development|test|production (default development); `DATABASE_PATH` and `TRUSTED_PROXY_HOPS` are required only when `APP_ENV=production` (T8's render.yaml must set them); `TRUSTED_PROXY_HOPS` 0..10.
6. Stored instants have whole-second precision (`Clock.now()` drops microseconds), so "+1 s" boundaries are exact.
7. Control characters rejected = Unicode category Cc plus line/paragraph separators (U+2028/2029). Leading/trailing whitespace is trimmed in text fields; passwords are not trimmed.
8. `cancel_allowed` looks only at time (not class status): a studio-cancelled class's bookings are already cancelled, so T5's "already cancelled" no-op comes first in the fixed rule order.
9. F26 (empty routers in the factory) is T2, not done here. Admin bootstrap, auth, CSRF, headers, body-size limit are T2/T3.

## Could not do
- `docker build` / container run: no Docker daemon here. Dockerfile and the CI docker job are untested.
- CI workflow cannot be run; action versions (`checkout@v4`, `setup-python@v5`, `gitleaks-action@v2`; the gitleaks action may need a licence secret for organisation repos) should be checked on first push.
- pip-audit not run (not installed, no network use).

HANDOFF
From: developer            To: pr-reviewer
Status: DONE
Summary: T1 walking skeleton and shared kernel implemented (config, time, rules, db/write_tx/migrations, 0001 schema, validators, JSON logging, /health, generic 500, Dockerfile, CI file). 84 tests pass.
Artifacts: branch feat/T1-skeleton-kernel; .autocraft/work/T1/handoff-1.md
Open items: 1. Diff over 400 lines (see deviation 1). 2. Docker/CI/pip-audit unrun. 3. tzdata pin unverified. 4. Stricter bookings CHECK (deviation 4): confirm OK for T4/T5.
Next: review per protocol s12; write .autocraft/work/T1/review-1.md with a VERDICT line. Human merges.
