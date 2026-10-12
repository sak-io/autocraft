# T4 handoff 1: schedule, class page, admin class management

Branch `feat/T4-schedule-admin` (from main after T2). Owns `classbook/routes/classes.py` and `classbook/web/templates/classes/`.

## What and why
- `GET /` lists active classes with `now < start <= now+60d` (SQL prefilter, then `rules.is_listed`), ordered by start. State per class comes from one function (`state_of`): cancelled / started / opens_later (greyed, "Opens for booking on <London date time>" from `rules.opens_at`, no action) / full ("Full", no action) / bookable. Bookability is `rules.is_bookable`, never a local rule.
- `GET /classes/{id}`: visitor sees "Sign in to book" -> `/login?next=/classes/{id}`; student sees a Book form posting to `/classes/{id}/book` (T5 implements it); admin sees a manage link; other states show the reason. 404 for unknown id.
- Admin (`require_admin`): list (`/admin/classes`), new, create, detail with roster, edit, update, cancel.
- Edit/capacity: booked count, the capacity check and the UPDATE run in one `write_tx` (race-safe). Cancel: class status and `bookings -> cancelled, cancelled_by='studio'` in one `write_tx`; no emails. Create/edit reject a start `<= now` (now read inside the lock), DST-gap times (kernel `parse_london_input`), blank/over-limit fields (kernel validators). Fold takes first occurrence (kernel).
- M-3 (T2 review): `tests/test_templates_scan.py` now has `missing_csrf(directory)`; the self-test runs the real scan on a temporary bad/good/GET template set.

## Verify
```
python -m pytest -q                    # whole suite
python -m pytest -q tests/test_classes.py tests/test_templates_scan.py
```
Pytest summary (whole suite): `212 passed, 1 warning in 6.18s` (162 before + 50 new/changed; the warning is the known starlette/httpx deprecation).

Tests (`tests/test_classes.py`): listing order/fields/empty/hidden; day 30 and day 60 edges compared with `is_bookable`/`is_listed` (+-1 s); greyed London opens-on text; label disappears as the clock advances; sign-in link; XSS escaping (title, instructor, student name) on every page; student/visitor denied on all 7 admin routes (override seam `current_user`) and nothing changed; missing CSRF 403; create/validation per field incl. past, now, gap, fold; edit (prefill, past, gap, cancelled/started 409); capacity lowering refused (blocked-on-lock test with a booking transaction held open, plus 9-thread race); cancel atomic (trigger forces the 2nd statement to fail, class stays active), idempotent, 503 on lock timeout.

## Choices where the architecture was silent / deviations
1. Roles in tests: `app.dependency_overrides[current_user]`, users as fixture rows; CSRF in tests by setting the `csrf` cookie and the same form value (double-submit), so role checks are not masked by CSRF 403.
2. Class page is always `Cache-Control: no-store` (spots left is live data and signed-in pages embed a token) - F22 satisfied also for visitors.
3. Admin list shows only "Your previous sign-in" read from `users.prev_login_at`; the "failures since" count belongs to T3 (not shown).
4. Admin cancel of an already-started but active class is allowed server-side (api.md lists no 409 there); UI offers the button for any `active` class. Edit of started/cancelled class: 409 page. Capacity-below-bookings: 409 re-render of the form with the explanation on the capacity field. Other validation: 422.
5. Student page shows "You are booked on this class" (read-only query on `bookings`) instead of Book; the Book endpoint and double-booking rules stay T5's.
6. Error refusals use the existing `error.html` through `render()` (no edit to `web/__init__.py`; M-2 mapping stays T3's).
7. Shared-file edits (additive/minimal): `style.css` (+3 lines), `tests/test_web_shell.py` (removed the assertion that routers are empty, it cannot hold once any task fills one; T3/T5 will make the same one-line deletion), `tests/test_templates_scan.py` (M-3). `app.py`, `conftest.py`, `base.html` untouched. No services/ package created (logic is in the router module, ~225 lines) to avoid add/add conflicts with T3/T5.
8. Admin form uses `<input type=datetime-local>`; server also accepts "YYYY-MM-DD HH:MM". The list is not paginated (api.md).

## Not done / not run
- No real uvicorn/browser pass, CSS minimal and unchecked visually. Book endpoint, my-bookings, login (other tasks): links point to them. Route-guard enumeration is T7's.

```
HANDOFF
From: developer            To: pr-reviewer
Status: DONE
Summary: T4 done: public schedule (60-day horizon, greyed beyond 30 days via kernel rules), class page with sign-in link / Book form, admin list/new/edit/detail+roster/cancel with write_tx for capacity lowering and atomic studio cancel; M-3 template-scan self-test now runs the real scan. 212 tests pass.
Artifacts: branch feat/T4-schedule-admin; .autocraft/work/T4/handoff-1.md
Open items: 1. Cancel of started-but-active class allowed (choice 4). 2. Class page always no-store (choice 2). 3. Removed "routers are empty" assertion in test_web_shell (choice 7). 4. No browser pass.
Next: review per protocol s12 into .autocraft/work/T4/review-1.md with a VERDICT line. Human merges.
```
