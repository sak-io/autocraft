# T4 review, round 1: schedule, class page, admin class management

Reviewer: pr-reviewer. Branch `feat/T4-schedule-admin` vs `main`. Not edited by me. Full suite run by me: 212 passed.
Method: read the diff and architecture/spec/api rows, ran the suite, ran 13 mutations of `classbook/routes/classes.py` against `tests/test_classes.py` (in a copy), and probed 3 behaviours directly.

## Summary
Solid work. Rules come from the kernel (`is_listed`, `is_bookable`, `opens_at`, `SPOTS_LEFT_SQL`); the listing prefilter only uses `rules.LISTING_HORIZON` and the kernel decides. Capacity check and UPDATE are inside one `write_tx` with `now` read after the lock; class cancel is one transaction. Every admin route has `Depends(require_admin)`; roster and emails appear only on the admin detail page. Templates are autoescaped; flash text is static. One real test gap (MAJOR) must be closed; the rest is MINOR.

## Acceptance criteria
| AC | Verdict | Evidence |
|---|---|---|
| 1.1 order/fields, 60-day horizon, greyed >30d | OK | `classes.py:61-69`, tests `test_schedule_lists...`, `test_day_30_and_60_edges...` (+-1 s, compared with kernel) |
| 1.2 started/cancelled hidden | OK | SQL `status='active' AND starts_at > now`, plus `is_listed`; `test_schedule_hides...` |
| 1.3 empty message | OK | `schedule.html:5` |
| 1.4 Full, no action | OK | `schedule.html:15`; `test_full_class...` |
| 1.5 greyed, London opens-on, no action | OK | `schedule.html:13`, `opens_at`; BST case tested |
| 2.3 page + sign-in link | OK | `detail.html:26`; `next` path is a plain `/classes/{id}` |
| 3.6/3.7 listing side | OK | single `state_of` -> `rules.is_bookable`; label disappears with clock (test) |
| 5.1-5.3 | OK | `classes.py:135-152`; per-field 422; visitor 303, student 403 on all 7 routes (test) |
| 6.1 roster | OK, test gap (M-1) | `classes.py:161-163` |
| 6.2 capacity lowering | OK | check inside `write_tx` (`:189-200`); blocked-on-lock test and 9-thread race; mutation removing the check is caught |
| 6.3 cancel | OK | one `write_tx`, `cancelled_by='studio'`; atomic test uses a trigger; mutation `studio->student` caught |
| 6.4 non-admin denied | OK | all admin routes guarded; CSRF 403 checked |

## Findings

### [MAJOR] M-1 Roster "booked only" filter is untested (AC-6.1)
`classbook/routes/classes.py:163` filters `b.status = 'booked'`. I removed that filter in a copy and all 50+ tests in `tests/test_classes.py` still passed. After a studio cancel (or a student cancel in T5) the roster would then list people as booked. `test_admin_detail_shows_roster_and_spots_left` (`tests/test_classes.py:251`) only has one booked student. Add a test: one booked and one cancelled booking (and one after class cancel) -> only the booked student's name/email is on the page and "spots left" is consistent. (I confirmed the current code is correct: after cancel the roster is empty.)

### [MINOR] m-1 Huge numeric id gives HTTP 500 instead of 404
`GET /classes/99999999999999999999999` (public) and `/admin/classes/<same>` raise `OverflowError` from sqlite at `classes.py:44` -> 500 (api.md: unknown id -> 404). No data leak, but an unauthenticated URL can produce error logs/alerts. Fix in `get_class` (catch `OverflowError` -> 404, or declare `class_id: int = Path(ge=1, le=2**63-1)` and map to 404) and add a test. Same helper will be reused by T5, so fix once.

### [MINOR] m-2 Cancelling an already-started class rewrites attendance history
`classes.py:218-222` (`admin_cancel`) only checks `status == 'active'`; `admin_detail.html:12` offers the button for started classes. Probe: cancelling a class that started an hour ago returned 303 and turned its `booked` rows into `cancelled`/`studio` (verified). The spec/api are silent (api.md row 13 lists no 409), and the developer flagged it, so it is not a blocker, but the effect is that people who attended appear "cancelled by the studio" and the roster for that class empties. Recommended: refuse with 409 for `started` (consistent with edit, api row 12), hide the button, add a test; if the owner prefers to keep it, record it as an ADR/decision in the spec and add a test pinning the behaviour. Please state which in the handoff. Not tested either way today.

### [MINOR] m-3 Greyed rows may fail contrast
`style.css:+4` (`.class.greyed { opacity: .65 }`) on top of `.muted` (#5b6770 on white) gives roughly 2.8:1, below WCAG AA 4.5:1 for the "Opens for booking on ..." text, which is the important information. Same in dark mode. Keep the dashed border/greying but apply opacity only to the title block, or use a colour that still has 4.5:1; T7 will check a11y but better fixed here.

### [MINOR] m-4 Cancel message branch untested
Mutating `done = row["status"] == "active"` to `True` (`classes.py:218`) survives: `test_cancel_twice_is_a_no_op` checks `cancelled_at` unchanged but not the flash text "That class was already cancelled." Assert the second response's flash/redirect target text. (Harmless in effect because the UPDATE of 0 booked rows is idempotent, hence MINOR.)

### [NIT] n-1 Capacity message hidden by other errors
`classes.py:197` requires `not errors`, so a bad capacity-vs-bookings is only reported after other fields are fixed, and then as 409. Acceptable; maybe mention in a comment.
### [NIT] n-2 `view()` computes `opens` for every class including ones where it is not shown; trivial.
### [NIT] n-3 `docs/STATUS.md` is not updated in this branch (protocol rule 7); fine if the coordinator does it on merge.

## Checked and fine (no action)
- XSS: title, instructor, student name rendered through Jinja autoescape on schedule, detail, admin list/detail/edit (value attribute is quoted); flash texts are server constants, and the flash cookie is HTML-escaped by `base.html:28`. Test covers `<script>`, `<img onerror>` and a student name on 5 pages.
- Day-30 / day-60 edges: tested at -1 s, 0, +1 s against kernel predicates; mutating the 30-day window by 1 s is caught.
- DST: gap rejected via kernel `parse_london_input` (create and edit, 422), fold takes first occurrence (tested).
- IDOR: no per-user object routes in T4; the "you are booked" lookup uses `user.id` from the session.
- Roster privacy: emails only in `admin_detail.html:9` behind `require_admin`; public pages show only counts.
- Edit/cancel of started or cancelled classes: edit -> 409 (GET and POST); cancelled class cancel is a no-op 303.
- Race: `get_class` and the UPDATE are in the same `BEGIN IMMEDIATE`; T5's booking (same lock) cannot slip in between.
- Cache: class page is `no-store` (F22); mutation removing it is caught.
- A11y basics: `lang="en"` in base, one `h1` per page, `h2` per class card, labelled inputs with `for`/`id`, errors linked with `aria-describedby`, table `scope` headers.
- Test-suite change in `test_web_shell.py` (removed "routers are empty") is justified; M-3 scan self-test now runs the real scan (good).

## Needed for approval
Fix M-1. Please also address m-1 to m-4 or reply with a reason (m-2: say which option you chose).

VERDICT: CHANGES REQUESTED
