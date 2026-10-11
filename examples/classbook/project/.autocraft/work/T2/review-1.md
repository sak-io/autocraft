# T2 review, round 1 (pr-reviewer)

Branch `feat/T2-web-shell` (3 code commits + handoff; 20 files, ~985 lines of which ~430 tests). Checked against the work-breakdown T2 row, architecture s5, api.md conventions, threat model T-6/T-9, F22/F26.

## What I ran
- `pytest`: 162 passed (84 from T1 + 78 new), 1 known harmless warning.
- Two real uvicorn servers (dev hops=0, prod hops=1 with `--no-proxy-headers`) with a probe factory in /tmp (route additions only; branch untouched), driven by curl:
  - Headers (CSP, nosniff, X-Frame-Options, Referrer-Policy, x-request-id) present on 200, 404, CSRF 403, 413 (content-length and chunked), 500. HSTS only in production.
  - POST with no cookie/token: 403, `no-store`. Over-16 KB body: 413 by content-length and by chunked streaming.
  - Anonymous request to a guarded route: 303 `/login?next=/me`.
  - `safe_next`: `//evil.com`, `/\evil.com`, `%2f%2fevil`, `/%2f%2fevil`, `/%5cevil`, `javascript:alert(1)`, `https://x`, `/x:y`, `/..//evil`, `%09`, `%0d%0a`, a literal tab, 600 chars: all return `/`. `/ok?x=1` and `/classes/5` pass.
  - `client_ip` hops=1: `6.6.6.6, 1.2.3.4` gives 1.2.3.4; two XFF header lines are joined and the right-most wins; no header gives the socket address.
- TestClient probes (dev and production): page using `csrf_field()` sends `Cache-Control: no-store` and sets the cookie (production: `__Host-csrf; Path=/; HttpOnly; SameSite=Lax; Secure`); cookie equals the embedded token; valid POST 200; one-character-wrong token, JSON body and PUT without token all 403; a second GET reuses the token and sets no new cookie.
- Mutation checks on the template scan: removing `csrf_field()` from `base.html` fails `test_every_post_form_uses_csrf_field`; adding an upper-case `<FORM METHOD=POST>` template without the field fails it too. So the scan does catch the failure it exists for.

## Checklist result
1. T2 acceptance: all met (POST without valid token 403 with and without a session; every api.md header; client IP uses only the trusted hop; `next` rejects the required classes; CSRF with and without cookie; template scan; F22 no-store; F26 routers registered in the factory; auth seams overridable; Mailer protocol).
2. Correctness: body is read once, size-limited, then replayed to CSRF and to the route (verified with a real POST through all layers). Middleware order is sound: SecurityHeaders outermost so error pages carry headers, RequestContext inside it so the generic 500 is covered, BodyLimit before CSRF so CSRF never buffers an oversized body.
3. Tests: assert behaviour and are the right set. See M-3 for one gap.
4. Security: constant-time compare, shape-checked cookie, token only from the form body (query string and header ignored, tested), non-form content types refused, `__Host-` plus `Secure` in production, errors do not echo input. Findings below are hardening only.
5. Design fit: matches architecture s5 and api.md. Re-implements nothing from T1.
6. Maintainability: small modules with why-comments, no dead code.
7. Operability: CSRF rejections are logged with reason and path only.
8. CI: not observable here (no GitHub); local suite green. Same condition as T1: first CI run must be green before the human merge.

## Judgement on the developer's flagged choices
1. Unsigned flash cookie: accepted. It carries only display text, is always autoescaped (Jinja autoescape for .html; tested with markup), capped at 3 x 160 chars, HttpOnly, and an attacker who can set it already controls that browser. Signing would need a new secret, which the architecture avoids. Condition: never put anything that triggers an action or a link target in a flash (text only). Add that as a comment in `templating.py` (see N-1).
2. `client_ip` fallback to the socket address: accepted; it fails safe (never a client-written value) and cannot be induced from outside because the proxy always appends an entry. See M-1 for a related uvicorn setting.
3. `no-store` depending on guards: accepted. Pages only receive `user` via a guard (`request.state.user`), so a route without a guard also shows nothing user-specific; the two always travel together. T7's guard-enumeration test closes the remaining gap.
4. Middleware order: correct (see Checklist 2).
5. `safe_next` stricter than api.md (rejects any inner `//`, `/x:y`, >512): accepted, and safer; it only ever falls back to `/`.

## Findings

### [MINOR]
- M-1 `Dockerfile` CMD (T1 file, relevant now): uvicorn's default `--proxy-headers` rewrites the socket address from `X-Forwarded-For` when the peer is 127.0.0.1. I confirmed it: with `TRUSTED_PROXY_HOPS=0` on a dev server, `curl -H 'X-Forwarded-For: 6.6.6.6'` makes `client_ip` return 6.6.6.6. Harmless on Render (peer is not loopback) but it makes `client_ip` depend on a second, implicit mechanism. Add `--no-proxy-headers` to the Dockerfile CMD and the `.env.example` run line so `client_ip` is the only place XFF is interpreted (with it, my prod probe behaved exactly as designed).
- M-2 `web/__init__.py:16-20`: `_MESSAGES` knows only 403/404/405; 401/409/422/429/503 raised as `HTTPException` fall to "Something went wrong / Please try again". Work breakdown T7 requires readable 429/503 pages and api.md uses 409/422/429. Add 429 ("Too many attempts, try again later") and 503 now (cheap, and T3 needs 429 on day one), or state that T3/T5 render their own.
- M-3 `tests/test_templates_scan.py`: `test_scan_would_catch_a_missing_field` only re-checks the regex on a string; it does not exercise the real scan against a bad template. Make `forms()` take a directory and run it on a `tmp_path` template that omits the field (assert it is reported), so the guard cannot rot silently. (My manual mutation shows the scan does work today.)

### [NIT]
- N-1 `templating.py`: add the comment "flash text only: never use it to carry URLs or actions" next to the unsigned-cookie note.
- N-2 `test_templates_scan.py`: a `csrf_field()` mentioned in a Jinja comment (`{# csrf_field() #}`) or a method set by `{% if %}` evades the scan. Contrived; optionally strip `{# ... #}` before matching and require a literal `method=` in the tag.
- N-3 `csrf.py`: cookie has no `Max-Age` (session cookie), so the token lasts until the browser closes; fine, rotation at login/logout is T3's job. T3 must call `rotate_csrf` on both (api.md #4, #5) and must test it.
- N-4 `mail/__init__.py`: `NullMailer` silently drops mail; T6 must replace it in `build_mailer` and the T6 test must fail if `NullMailer` is still wired (add to T6 brief).
- N-5 The nav (`base.html`) links to routes not yet implemented (`/login`, `/signup`, `/my-bookings`, `/admin/classes`); expected until T3-T5, but it should not ship to users before they exist.
- N-6 No real browser pass (declared); CSS and focus rings are unchecked. T7 manual checklist covers it.

### [PRAISE]
- P-1 Header and no-store handling is done once in middleware rather than per route, so error pages cannot forget headers; the test that 403/413/500 carry them is the right one.
- P-2 Body limit works for chunked bodies and is tested at exactly 16 KB (allowed) and over (413).

## Size
~985 lines, about 430 of them tests; one coherent layer, commits split by concern. No split needed.

No open BLOCKER or MAJOR. MINOR M-1..M-3 are small; per the review rules they may be fixed now or tracked (M-1 and M-2 are best done before T3 starts).

```
HANDOFF
From: pr-reviewer            To: developer
Status: DONE
Summary: T2 approved. 162 tests pass; real uvicorn probes confirm headers on 403/404/413/500, CSRF with/without cookie, no-store on token pages, chunked body limit, XFF handling and next validation. 0 BLOCKER/MAJOR, 3 MINOR, 6 NIT.
Artifacts: .autocraft/work/T2/review-1.md
Open items: M-1 add --no-proxy-headers; M-2 add 429/503 error messages; M-3 make the template-scan self-test run the real scan; N-3/N-4 into T3/T6 briefs.
Next: orchestrator commits the review, applies or tracks the MINORs; human merges after first green CI.
```

VERDICT: APPROVED
