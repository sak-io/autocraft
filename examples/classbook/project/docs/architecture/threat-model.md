# Threat model: ClassBook (round 2)

## Assets
A1 student personal data (name, email, bookings). A2 admin account (sees all students, changes all classes). A3 booking integrity. A4 password hashes and session tokens. A5 availability. A6 backups (contain A1, A4, including admin downloads kept by humans). No payment data.

## Trust boundaries
Browser -> host proxy -> app (all browser input untrusted, including `X-Forwarded-For` beyond the trusted hop); app -> SQLite on local disk; app -> mailer (later external); human-held backup downloads; CI/dependencies -> build.

## Threats and mitigations
| ID | Threat | Mitigation | Verified by |
|---|---|---|---|
| T-1 | Student reads/cancels another's booking | Ownership in SQL from session user; 404 | T7 authz matrix (AC-4.4) |
| T-2 | Non-admin uses admin routes | Single guard per route, deny by default; enumeration test fails on any unguarded non-public route | T7 route test (AC-5.3, 6.4) |
| T-3 | Overbooking or duplicate via race/double click | `write_tx` (`BEGIN IMMEDIATE`) + derived count + partial unique index | thread test + real-HTTP race (AC-3.3, 3.4) |
| T-4 | Password guessing | scrypt; throttle per email (10/15 min, any IP) and per IP (20/15 min), stored in SQLite; generic errors; dummy hash for unknown emails; admin password >=14. Residual: an attacker can delay logins for an email up to 15 min | T3 tests incl. spoofed forwarded headers |
| T-5 | Session theft/fixation | 256-bit token, hashed at rest, HttpOnly, Secure (production), SameSite=Lax, `__Host-` prefix, new session at login, 14-day expiry, purge | T3 tests |
| T-6 | CSRF incl. login CSRF | Double-submit cookie valid before sessions, rotated at login/logout, SameSite=Lax | T2 tests; template scan |
| T-7 | XSS | Autoescape, CSP, no inline script, control characters rejected | T4 test |
| T-8 | SQL injection | Parameterised SQL only; reviewer greps for string-built SQL | tests with quotes |
| T-9 | Open redirect via `next` | Strict validation (api.md header) | unit tests incl. `/\evil.com`, `%2f` |
| T-10 | Account enumeration | Generic login errors, dummy hashing; sign-up duplicate message generic. Residual: timing and repeat-sign-up signal until verification exists | – |
| T-11 | Secret leakage | Env only; refuse start on missing/weak; logs omit secrets/cookies/bodies; secret scan in CI | CI, T1 log test |
| T-12 | Data loss | DB constraints, nightly in-app copy, host snapshots, monthly admin download; restore rehearsed | T8 |
| T-13 | Personal data in backups/logs | Admin download is admin-only over HTTPS and `no-store`; humans told to keep copies private; logs omit email bodies; deletion script and its backup-age caveat | runbook review |
| T-14 | Vulnerable dependency | Pinned versions, `pip-audit` in CI, few dependencies | CI |
| T-15 | Denial of service / abuse | Body cap 16 KB, field limits, per-user 20 actions/hour, sign-up throttle, lock timeout -> 503 | tests |
| T-16 | Tests/dev emailing real people | Only `recording` backend accepted in phase 1 | config test |
| T-17 | Mail abuse: attacker signs up with a victim's address so confirmations (with attacker-chosen name) reach the victim; header injection; mail flooding | Real delivery must not be enabled before email verification exists; control characters rejected; 20 mail-causing actions/hour/user | config test; ADR-0004 gate |
| T-18 | Client-IP spoofing | Only the right-most trusted hop of `X-Forwarded-For` is used | T3 test |
| T-19 | Stray or hijacked admin role | One-admin unique index; bootstrap refuses to promote an existing student or change the admin email without explicit flags | T3 tests (3 cases) |

## Named accepted risk
**AR-1 (accepted by Maya, 2026-10-10): the admin login has a strong password only: no second step (MFA) and no automatic reset.** It exposes all student names and emails if the password is guessed or leaked. Mitigations: >=14-char password, throttle, "last sign-in" note on the admin page. Recovery: Maya's nephew Tom (or any developer) sets a new `ADMIN_PASSWORD` in the host dashboard and redeploys (runbook step in T8); the app resets the stored admin password on startup. Revisit when real email and verification are connected.
