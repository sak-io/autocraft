# T2 handoff 1: web shell

Branch `feat/T2-web-shell` (from main, contains T1). No GitHub: this file is the pull request (protocol s12).

## What and why
Imports the T1 kernel/config; re-implements nothing. All new code is in `classbook/web/`, `classbook/routes/`, `classbook/mail/`.
- `web/csrf.py` + `web/middleware.py` `CsrfMiddleware`: double-submit token that works with no session. Cookie `__Host-csrf` (plain `csrf` unless `APP_ENV=production`), HttpOnly, SameSite=Lax, Path=/, Secure in production. Every non-GET/HEAD/OPTIONS request needs form field `csrf_token` == cookie (`compare_digest`) else 403 page. `csrf_field()` is a Jinja global; calling it also marks the page `Cache-Control: no-store` and makes the middleware set the cookie if absent (F22, automatic, no per-route code). `rotate_csrf(request)` is the hook T3 calls at login/logout.
- `SecurityHeadersMiddleware` (outermost, so 403/413/404/500 pages get them too): CSP `default-src 'self'`, nosniff, X-Frame-Options DENY, Referrer-Policy same-origin, HSTS (`max-age=31536000`) only in production, `no-store` when a page asks (csrf_field, flash shown, any signed-in user).
- `BodyLimitMiddleware`: 413 over 16 KB (`MAX_BODY_BYTES` from T1), by declared Content-Length and while streaming chunked bodies.
- `web/util.py`: `client_ip(request, hops=None)` (Nth entry from the right of X-Forwarded-For), `safe_next()`, `login_url()`.
- `web/deps.py`: `User`, seam `current_user` (default: nobody; T3 overrides, T4/T5 tests override with fixtures), `optional_user` (public), `require_user`, `require_student`, `require_admin`, `get_settings/get_clock/get_mailer`. Anonymous -> 303 `/login?next=<path>` (GET only), wrong role -> 403.
- `web/templating.py`: `render(request, name, ctx, status)`, `flash(request, response, text, level)`, templates `base.html` (nav, skip link, flash region, logout form with csrf_field) and `error.html`; `web/static/style.css` (CSP forbids inline styles, so external file; focus ring, dark mode).
- `mail/__init__.py`: `Mailer` protocol, `NullMailer` placeholder, `build_mailer(settings)` seam (T6 fills it; the factory is not edited).
- `routes/{accounts,classes,bookings}.py`: empty routers, listed in `routes.ROUTERS`, included by the factory (F26). `web.install()` wires middleware, static files, error handlers.

## How to verify
```
PY=/tmp/claude-0/-home-user-autocraft/4dc487e6-d297-5355-ab6e-8239135c933c/scratchpad/venv/bin/python
$PY -m pytest ; $PY -m compileall -q classbook tests
```
Tests: `tests/test_web_util.py` (next validator incl. `//`, `/\`, `%2f`/`%5C`, schemes, control chars, encoded CR/LF; IP helper incl. spoofed left entries, short/garbage header, IPv6), `tests/test_web_shell.py` (CSRF with and without cookie, wrong/missing/query/header/JSON token, malformed cookie, rotation, no-store (F22), headers on 200/404/403/413/500, production cookie+HSTS, 16 KB boundary and chunked, flash escaping and one-time, role seams, empty routers, mailer seam), `tests/test_templates_scan.py` (every `<form method=post>` contains `csrf_field()`; every form states a method).

## Test evidence
`162 passed, 1 warning in ~3s` (84 from T1 + 78 new; the warning is the known starlette/httpx TestClient deprecation).

## Choices where the architecture was silent / deviations
1. **Flash cookie is unsigned** (no secret exists to sign with; architecture says no other secrets). HttpOnly, always HTML-escaped, max 3 messages x 160 chars, cleared when shown; a forged one can only show text to the browser that set it. Say if you want it signed with a derived key.
2. `client_ip`: if X-Forwarded-For has fewer entries than hops, or the chosen entry is not a valid IP, it returns the socket address (never a client-written value). Behind the proxy that would lump callers together for throttling, which fails safe.
3. `safe_next` is stricter than the api.md text: also rejects encoded control characters (`%00`-`%1f`, `%7f`), a scheme-looking first segment (`/x:y`), U+2028/2029/0085, values over 512 chars, and returns "/" for any invalid value.
4. CSRF only accepts `application/x-www-form-urlencoded` bodies (no multipart/JSON POSTs exist). Unsafe = any method not GET/HEAD/OPTIONS.
5. `no-store` for "authenticated pages" is implemented in `optional_user`: every route using a guard dependency is marked once a user is present. A page that never calls a guard does not know the user, so T3/T4/T5 routes must declare their guard (T7's enumeration test enforces that anyway).
6. Middleware order outer->inner: SecurityHeaders, RequestContext (T1), BodyLimit, Csrf. So T1's generic 500 page now also carries the headers. `RequestContextMiddleware` is no longer added in `app.py` but inside `web.install()`.
7. Error pages: HTTPException (403/404/405/...) render `error.html` (HTML, no detail echoed). The 403 for CSRF and 413 are tiny standalone pages from middleware.
8. `NullMailer` (drops mail) is the default until T6 supplies `RecordingMailer`; it exists only so `app.state.mailer` is never missing.
9. Nav links (`/login`, `/signup`, `/my-bookings`, `/admin/classes`, `/logout`) point at routes the later tasks create.

## Not done / not run
- No real uvicorn/browser pass (TestClient only); CSS is minimal and not checked visually. Docker image not rebuilt (templates/static live inside the `classbook` package, which the Dockerfile already copies).
- Route-guard enumeration is T7's. Rotation is provided, but calling it at login/logout is T3's.

HANDOFF
From: developer            To: pr-reviewer
Status: DONE
Summary: T2 web shell implemented: CSRF (cookie, no session needed, rotation hook), no-store on token pages (F22), security headers, 16 KB limit, client-IP and next helpers, guard seams, flash, base template, Mailer protocol, empty routers in the factory (F26). 162 tests pass (78 new).
Artifacts: branch feat/T2-web-shell; .autocraft/work/T2/handoff-1.md
Open items: 1. Unsigned flash cookie (choice 1). 2. client_ip fallback to socket (choice 2). 3. Guard-dependent no-store (choice 5). 4. No real-browser check.
Next: review per protocol s12; write .autocraft/work/T2/review-1.md with a VERDICT line. Human merges.
