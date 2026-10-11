# ADR 0003: Email+password auth with stdlib scrypt and server-side sessions

- **Status:** Accepted (conditions from principal-engineer review F7 adopted)  ·  **Date:** 2026-10-10

## Context
The authentication capability says use a provider or framework library rather than writing password and session code, and offers verification, reset and MFA. Here there is no mail service (so no verification or reset), one admin, and a tiny budget (Q1: email + password).

## Decision
Use vetted standard-library primitives: `hashlib.scrypt` (N=2^14, r=8, p=1, per-user salt, versioned hash prefix), `hmac.compare_digest`, `secrets.token_urlsafe(32)` session tokens stored as SHA-256 in the DB, cookie flags per architecture s5. Conditions: password length capped at 128; hashing/verifying runs outside any write transaction; unknown emails get a dummy verify; "no MFA for the admin" is named risk AR-1 (accepted by Maya); the hasher is one function behind a version prefix so it can be swapped. Verification, reset and MFA arrive with real email.

## Alternatives considered
1. Hosted auth provider (Auth0/Clerk/Supabase) - the capability default, but an extra account, cost and outside dependency for one studio, and it needs email for its own flows anyway; revisit when real email is connected.
2. Signed stateless cookies/JWT - logout cannot truly end a session; rejected.
3. argon2/bcrypt package - stronger default but a new dependency; later swap via the prefix.

## Consequences
We own a small amount of auth code, so T3 gets focused tests and reviewer attention.
