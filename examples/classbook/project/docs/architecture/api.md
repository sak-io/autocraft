# API contract: ClassBook (server-rendered HTML routes) - round 2

Conventions: times shown in Europe/London, stored UTC. Every POST needs form field `csrf_token` matching the CSRF cookie, including `/login` and `/signup` (else **403**). Unknown or foreign ids: **404**. Not signed in on a protected route: **303 -> `/login?next=<path>`**. Wrong role: **403**. POST success: **303** with a flash message. Validation failure: re-render, **422**, per-field messages. Rule refusal: **409** with explanation. Lock timeout: **503**. Throttled: **429**.
`next` is accepted only if it starts with exactly one `/`, contains no backslash, control character, `//`, scheme or `%2f`/`%5c` (any case); otherwise ignored (-> `/`).
Auth levels: Public, Student, Admin, Any user.

| # | Method + path | Auth | Request | Success | Errors |
|---|---|---|---|---|---|
| 1 | `GET /` | Public | – | 200 schedule of active classes with `now < start <= now+60d`, ordered by start: title, start, duration, instructor, spots left. Bookable (`start <= now+30d`): Book link to `/classes/{id}`, or "Full" with no action when 0 spots. Beyond 30 days: greyed, "Opens for booking on <date time>", no action. Friendly empty message (AC-1.1-1.4, 3.6, F21) | – |
| 2 | `GET /classes/{id}` | Public | – | 200 class details. Visitor: "Sign in to book" -> `/login?next=/classes/{id}`. Student: Book button (POST #6) if bookable, else the reason (full, opens on date, started, cancelled). Admin: link to admin detail (AC-2.3) | 404 unknown |
| 3 | `GET/POST /signup` | Public | `name`, `email`, `password` (10..128), `csrf_token` | 303 -> `next` or `/`, signed in, new session (AC-2.1) | 422 fields (limits per architecture s3); 422 generic "could not create account with these details" if email exists (AC-2.2); 429 (10/hour/IP) |
| 4 | `GET/POST /login` | Public | `email`, `password`, `next?` | 303 -> validated `next` or `/`, new session, CSRF token rotated (AC-2.3) | 401 generic message (AC-2.4); 429 (10 fails/15 min per email, 20 per IP) |
| 5 | `POST /logout` | Any user | – | 303 -> `/`; session row deleted; CSRF rotated | no session: 303 -> `/login` |
| 6 | `POST /classes/{id}/book` | Student | – | 303 -> `/my-bookings` "Booked" (AC-3.1); already booked: 303 "already booked", nothing created (AC-3.4) | Checked **in this order** with one `now` read inside the write transaction: 404 unknown -> 409 `started_or_cancelled` (AC-3.5) -> 409 `too_far_ahead` with opens-on date (AC-3.6) -> already booked (no-op) -> 409 `full` (AC-3.2/3.3). Also 429 (20 actions/hour/user); admin 403; anonymous 303 to login |
| 7 | `GET /my-bookings` | Student | – | 200 own upcoming `booked` bookings, plus upcoming ones cancelled by the studio shown greyed "cancelled by the studio" (AC-4.1, F18). Own cancelled-by-student rows are not shown | – |
| 8 | `POST /bookings/{id}/cancel` | Student | – | 303 "Cancelled" if `start - now >= 12h` (AC-4.2) | Order: 404 not found or not mine (AC-4.4) -> already cancelled: 303 no-op (AC-4.5) -> 409 `too_late` (<12h or started) (AC-4.3). 429 shared with #6 |
| 9 | `GET /admin/classes` | Admin | – | 200 all classes (upcoming, past, cancelled) with booked counts; "last sign-in" note | 403 |
| 10 | `GET /admin/classes/new`, `POST /admin/classes` | Admin | `title`, `starts_at` (London local), `duration_min`, `instructor`, `capacity`, `csrf_token` | 303 -> admin detail (AC-5.1) | 422 per field incl. blank title, capacity <1 or >200, non-integer, past start, non-existent London time, control characters (AC-5.2); 403 (AC-5.3) |
| 11 | `GET /admin/classes/{id}` | Admin | – | 200 details, spots left, roster of booked students (name, email) (AC-6.1) | 404; 403 |
| 12 | `GET /admin/classes/{id}/edit`, `POST /admin/classes/{id}` | Admin | as #10 | 303 -> detail | 422 (also start moved into the past); 409 `capacity_below_bookings` (AC-6.2); 409 class cancelled or started; 403 (AC-6.4) |
| 13 | `POST /admin/classes/{id}/cancel` | Admin | – | 303; class `cancelled`; its `booked` bookings -> `cancelled` with `cancelled_by='studio'`; no emails (AC-6.3) | 404; 403; already cancelled: 303 no-op |
| 14 | `GET /admin/backup` | Admin | – | 200 downloads a consistent copy of the database (`VACUUM INTO` temp file, `no-store`, deleted after sending) | 403 |
| 15 | `GET /health` | Public | – | 200 `{"status":"ok"}` after `SELECT 1` | 503 `{"status":"unavailable"}` |

Email side effects (after commit): #6 new booking -> one "booked" message; #8 new cancellation -> one "cancelled" message; none on refusals, no-ops or #13.
Headers on all responses: CSP `default-src 'self'`, nosniff, X-Frame-Options DENY, Referrer-Policy same-origin, HSTS (production); `no-store` on authenticated pages.
