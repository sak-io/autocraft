"""T7 (7): exploratory testing, kept as tests. Each test is something a hostile or confused person can do.

Defects found are written as strict xfail tests named D-n (see docs/qa/qa-summary.md): they FAIL TODAY by
design, and will start failing as "unexpectedly passed" the moment a developer fixes the defect, which is the
cue to delete the xfail marker (the test is then the regression test).
"""
import re
from datetime import timedelta

import pytest

from classbook.kernel import db
from classbook.kernel.timeutil import format_london
from tests.qa.support import (ADMIN_EMAIL, NOW, PASSWORD, TOKEN, AppBrowser, csrf_in, insert_booking, insert_class,
                              insert_user, one, rows, session_for)
from tests.qa.test_authz_matrix import fingerprint

HUGE = 99999999999999999999999


# ======================================================================================================
# Former defects: now regression tests
# ======================================================================================================
@pytest.mark.parametrize("path", [f"/classes/{HUGE}/book", f"/bookings/{HUGE}/cancel", f"/classes/{2**63}/book"])
def test_D1_huge_ids_on_book_and_cancel_are_404_not_500(world, path):
    b = AppBrowser(world.app, raise_server_exceptions=False)  # a 500 must show up as a status, not an exception
    b.cookies.set("session", session_for(world.path, world.ids["a"]))
    assert b.post_form(path).status_code == 404


@pytest.mark.parametrize("who,method,path", [(None, "GET", "/classes/abc"), ("admin", "GET", "/admin/classes/abc"),
                                             ("a", "POST", "/classes/abc/book"), ("a", "POST", "/bookings/1.5/cancel")])
def test_D2_non_numeric_ids_get_the_404_page_not_a_json_422(world, who, method, path):
    b = world.browser(who)
    r = b.post_form(path) if method == "POST" else b.get(path)
    assert r.status_code == 404 and r.headers["content-type"].startswith("text/html")


def test_D3_head_health_is_200(world):
    assert world.browser(None).head("/health").status_code == 200


def test_D4b_signed_in_user_sees_signed_in_menu_on_the_404_page(world):
    html = world.browser("a").get("/no-such-page").text
    assert "Sign out" in html and "Sign in" not in html


def test_D7_admin_page_shows_failed_sign_in_count_since_last_visit(world):
    with db.write_tx(world.path) as conn:
        conn.execute("UPDATE users SET prev_login_at='2026-10-09T08:00:00Z' WHERE id=1")
        for minute in range(7):
            conn.execute("INSERT INTO login_failures (key, at) VALUES (?, ?)",
                         (f"email:{ADMIN_EMAIL}", f"2026-10-09T09:{minute:02d}:00Z"))
    html = world.browser("admin").get("/admin/classes").text
    assert re.search(r"\b7\b[^<]{0,40}(failed|unsuccessful|attempt)", html, re.I), "failed attempts are not shown"


def test_D8_greyed_classes_show_no_spots_left_number(world):  # owner decision: spec amended
    html = world.browser(None).get("/").text
    far = re.search(r'<li class="class greyed".*?</li>', html, re.S).group(0)
    assert "Opens for booking on" in far and not re.search(r"\d+ spots? left", far)


# ======================================================================================================
# Clock edge cases, end to end over HTTP (FixedClock moves; everything else is the real stack)
# ======================================================================================================
def test_opening_instant_end_to_end_label_then_book_appears_and_works_without_admin_action(world):
    ids, clock = world.ids, world.clock
    start = NOW + timedelta(days=45)
    opens = start - timedelta(days=30)                     # NOW + 15 days exactly
    clock.set(opens - timedelta(seconds=1))
    anon, b = world.browser(None), world.browser("b")   # sessions are made 'now' (they last 14 days)
    page = anon.get(f"/classes/{ids['c2']}").text
    assert f"Opens for booking on {format_london(opens)}" in page and "<form" not in page.split("<main")[1].split("</main>")[0].replace('class="inline"', "")
    r = b.post_form(f"/classes/{ids['c2']}/book")
    assert r.status_code == 409 and format_london(opens) in r.text
    assert one(world.path, "SELECT COUNT(*) FROM bookings WHERE class_id=?", ids["c2"]) == 0
    clock.set(opens)                                         # one second later: AC-3.7
    sched = anon.get("/").text
    assert "Far Yoga" in sched and re.search(r'data-state="bookable"[^>]*>\s*<h2><a href="/classes/%d"' % ids["c2"], sched)
    assert 'action="/classes/%d/book"' % ids["c2"] in b.get(f"/classes/{ids['c2']}").text
    assert b.post_form(f"/classes/{ids['c2']}/book").status_code == 303


def test_cancel_cutoff_end_to_end_exactly_12_hours_is_allowed_one_second_less_is_not(world):
    ids, clock = world.ids, world.clock
    start = NOW + timedelta(days=3)
    with db.write_tx(world.path) as conn:
        bk = insert_booking(conn, ids["c1"], ids["b"])
    b = world.browser("b")
    clock.set(start - timedelta(hours=12, seconds=-1))
    r = b.post_form(f"/bookings/{bk}/cancel")
    assert r.status_code == 409 and "12 hours" in r.text
    assert one(world.path, "SELECT status FROM bookings WHERE id=?", bk) == "booked"
    assert "Too late to cancel online" in b.get("/my-bookings").text and "Cancel booking" not in b.get("/my-bookings").text
    clock.set(start - timedelta(hours=12))
    assert b.post_form(f"/bookings/{bk}/cancel").status_code == 303
    assert one(world.path, "SELECT status FROM bookings WHERE id=?", bk) == "cancelled"


def test_a_class_starting_this_second_is_over_for_everyone(world):
    ids, clock = world.ids, world.clock
    clock.set(NOW + timedelta(days=3))                        # c1 starts right now
    assert "Flow" not in world.browser(None).get("/").text
    assert "already started" in world.browser(None).get(f"/classes/{ids['c1']}").text
    assert world.browser("b").post_form(f"/classes/{ids['c1']}/book").status_code == 409
    assert world.browser("a").post_form(f"/bookings/{ids['booking_a']}/cancel").status_code == 409  # started: too late
    assert "Flow" not in world.browser("a").get("/my-bookings").text                                  # no longer 'upcoming'


def test_sixty_day_listing_edge_and_greyed_state_end_to_end(world):
    ids = world.ids
    with db.write_tx(world.path) as conn:
        insert_class(conn, (NOW + timedelta(days=60)).strftime("%Y-%m-%dT%H:%M:%SZ"), 4, "Day Sixty")
        insert_class(conn, (NOW + timedelta(days=60, seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ"), 4, "Day Sixty Plus")
        insert_class(conn, (NOW + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ"), 4, "Day Thirty")
        insert_class(conn, (NOW + timedelta(days=30, seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ"), 4, "Day Thirty Plus")
    html = world.browser(None).get("/").text
    state = {title: st for st, title in re.findall(r'data-state="(\w+)">\s*<h2><a href="/classes/\d+">([^<]+)</a>', html)}
    assert state["Day Thirty"] == "bookable" and state["Day Thirty Plus"] == "opens_later"
    assert state["Day Sixty"] == "opens_later" and "Day Sixty Plus" not in state
    assert state["Far Yoga"] == "opens_later"
    order = [t for t in re.findall(r'<h2><a href="/classes/\d+">([^<]+)</a>', html)]
    assert order == sorted(order, key=lambda t: {"Flow": 3, "Day Thirty": 30, "Day Thirty Plus": 30.00001, "Far Yoga": 45, "Day Sixty": 60}[t])


def test_sessions_last_exactly_14_days(world):
    b = world.browser("a")
    world.clock.set(NOW + timedelta(days=14, seconds=-1))
    assert b.get("/my-bookings").status_code == 200
    world.clock.set(NOW + timedelta(days=14))
    r = b.get("/my-bookings")
    assert r.status_code == 303 and r.headers["location"] == "/login?next=/my-bookings"


def test_expired_session_then_posting_an_old_form_is_sent_to_sign_in_and_nothing_happens(world):
    b = world.browser("b")
    page = b.get(f"/classes/{world.ids['c1']}")
    form_token = csrf_in(page.text)
    world.clock.set(NOW + timedelta(days=15))
    before = fingerprint(world.path)
    r = b.post(f"/classes/{world.ids['c1']}/book", data={"csrf_token": form_token})
    assert r.status_code == 303 and r.headers["location"] == "/login"
    assert fingerprint(world.path) == before


def test_opening_label_follows_the_30x24_hour_rule_across_the_spring_dst_change(world):
    """Observation O-2, pinned: opens-on is start minus 720 hours, shown in London time, so for a class just
    after the clocks go forward the label's wall-clock time is one hour earlier than the class time."""
    start = "2027-03-28T10:00:00Z"                         # 11:00 BST (clocks went forward at 01:00 GMT that day)
    with db.write_tx(world.path) as conn:
        cid = insert_class(conn, start, 3, "Spring Class")
    world.clock.set(NOW.replace(year=2027, month=2, day=20))
    html = world.browser(None).get(f"/classes/{cid}").text
    assert "Sun 28 Mar 2027, 11:00" in html
    assert "Opens for booking on Fri 26 Feb 2027, 10:00" in html


# ======================================================================================================
# Hostile input
# ======================================================================================================
def test_sql_injection_strings_are_stored_and_shown_literally_and_tables_survive(world):
    evil = "x'); DROP TABLE classes;--"
    admin = world.browser("admin")
    r = admin.post_form("/admin/classes", {"title": evil, "starts_at": "2026-11-20T10:00", "duration_min": "60",
                                           "instructor": "' OR '1'='1", "capacity": "5"})
    assert r.status_code == 303
    html = world.browser(None).get("/").text
    assert "x&#39;); DROP TABLE classes;--" in html
    b = AppBrowser(world.app)
    p = b.get("/login")
    b.post("/login", data={"csrf_token": csrf_in(p.text), "email": "' OR 1=1 --@x.io", "password": "' OR 1=1 --"})
    assert world.browser(None).get("/classes/1%20OR%201=1").status_code in (404, 422)  # 422: see D-2; never 200/500
    assert one(world.path, "SELECT COUNT(*) FROM classes") == 4 and one(world.path, "SELECT COUNT(*) FROM users") == 3


def test_unicode_titles_survive_every_layer_page_flash_cookie_and_email(world):
    title = "Yoga \U0001f9d8‍♀️ مرحبا é́ ‮RTL" + "\U0001f600" * 60
    assert len(title) <= 100
    admin = world.browser("admin")
    r = admin.post_form("/admin/classes", {"title": title, "starts_at": "2026-10-20T10:00", "duration_min": "60",
                                           "instructor": "Zoë 瑜伽", "capacity": "5"})
    assert r.status_code == 303
    cid = one(world.path, "SELECT id FROM classes WHERE title LIKE 'Yoga%'")
    b = world.browser("b")
    r = b.post_form(f"/classes/{cid}/book")
    assert r.status_code == 303 and len(r.headers.get_list("set-cookie")[-1]) < 4000
    assert title.split("‮")[0] in b.get("/my-bookings").text
    assert world.browser(None).get(f"/classes/{cid}").status_code == 200
    (subject, body), = rows(world.path, "SELECT subject, body FROM messages")
    assert title in subject and title in body


def test_extra_form_fields_cannot_change_who_books_or_what_role_a_new_account_gets(world):
    ids = world.ids
    a = world.browser("a")
    r = a.post_form(f"/classes/{ids['c2']}/book", {"user_id": str(ids["b"]), "status": "cancelled"})  # far class: refused anyway
    r = a.post_form(f"/classes/{ids['c1']}/book", {"user_id": str(ids["b"]), "class_id": "999"})
    assert rows(world.path, "SELECT user_id FROM bookings WHERE class_id=? ORDER BY id", ids["c1"]) == [(ids["a"],)]
    anon = AppBrowser(world.app)
    p = anon.get("/signup")
    r = anon.post("/signup", data={"csrf_token": csrf_in(p.text), "name": "Mallory", "email": "mal@example.com",
                                   "password": "another-password-1", "role": "admin", "id": "1"})
    assert r.status_code == 303
    assert rows(world.path, "SELECT role FROM users WHERE email='mal@example.com'") == [("student",)]
    assert AppBrowser(world.app).get("/admin/classes").status_code == 303
    r = world.browser("admin").post_form("/admin/classes", {"title": "Extra", "starts_at": "2026-11-20T10:00", "duration_min": "60",
                                                           "instructor": "I", "capacity": "5", "status": "cancelled", "id": "1"})
    assert rows(world.path, "SELECT status FROM classes WHERE title='Extra'") == [("active",)]


def test_signing_up_with_the_admins_email_is_refused_generically_and_never_makes_a_second_admin(world):
    anon = AppBrowser(world.app)
    p = anon.get("/signup")
    r = anon.post("/signup", data={"csrf_token": csrf_in(p.text), "name": "Fake Maya", "email": ADMIN_EMAIL.upper(),
                                   "password": "another-password-1"})
    assert r.status_code == 422 and "could not create an account" in r.text.lower()
    assert one(world.path, "SELECT COUNT(*) FROM users WHERE role='admin'") == 1


def test_a_huge_url_cookie_and_unusual_paths_never_cause_a_500(world):
    c = AppBrowser(world.app, raise_server_exceptions=False)
    for path in ("/" + "a" * 5000, "/classes/" + "9" * 5000, "/%ff%fe", "/classes/%00", "/classes/1%0d%0aSet-Cookie:x=y",
                 "/static/%2e%2e/config.py", "/static/..%5cconfig.py", "/login?next=" + "/a" * 5000, "/?q=" + "z" * 10000):
        assert c.get(path).status_code in (200, 303, 404, 422), path
    c.cookies.set("session", "A" * 8000)
    c.cookies.set("csrf", "B" * 5000)
    assert c.get("/my-bookings").status_code == 303


# ======================================================================================================
# Confused user: stale pages, two tabs, back button
# ======================================================================================================
def test_stale_book_button_after_the_studio_cancels_the_class_explains_and_books_nothing(world):
    ids = world.ids
    b = world.browser("b")
    page = b.get(f"/classes/{ids['c1']}")                       # the page with the Book button is open in a tab
    world.browser("admin").post_form(f"/admin/classes/{ids['c1']}/cancel")
    r = b.post(f"/classes/{ids['c1']}/book", data={"csrf_token": csrf_in(page.text)})
    assert r.status_code == 409 and "cancelled" in r.text
    assert one(world.path, "SELECT COUNT(*) FROM bookings WHERE user_id=? AND status='booked'", ids["b"]) == 0
    assert rows(world.path, "SELECT kind FROM messages") == []


def test_stale_cancel_button_after_studio_cancelled_is_a_quiet_noop_without_email(world):
    ids = world.ids
    a = world.browser("a")
    page = a.get("/my-bookings")
    world.browser("admin").post_form(f"/admin/classes/{ids['c1']}/cancel")
    r = a.post(f"/bookings/{ids['booking_a']}/cancel", data={"csrf_token": csrf_in(page.text)})
    assert r.status_code == 303
    assert "already cancelled" in a.get("/my-bookings").text
    assert rows(world.path, "SELECT cancelled_by FROM bookings") == [("studio",)]       # not rewritten as 'student'
    assert rows(world.path, "SELECT kind FROM messages") == []


def test_two_tabs_cancel_twice_frees_one_spot_and_sends_one_email(world):
    ids = world.ids
    a = world.browser("a")
    tab1, tab2 = a.get("/my-bookings"), a.get("/my-bookings")
    assert a.post(f"/bookings/{ids['booking_a']}/cancel", data={"csrf_token": csrf_in(tab1.text)}).status_code == 303
    assert a.post(f"/bookings/{ids['booking_a']}/cancel", data={"csrf_token": csrf_in(tab2.text)}).status_code == 303
    assert rows(world.path, "SELECT kind FROM messages") == [("cancelled",)]
    assert one(world.path, "SELECT COUNT(*) FROM bookings WHERE status='booked'") == 0
    assert "2 spots left" in world.browser(None).get("/").text


def test_logout_in_one_tab_kills_the_other_tabs_forms_and_a_replayed_request(world):
    ids = world.ids
    b = world.browser("b")
    page = b.get(f"/classes/{ids['c1']}")
    stale_token = csrf_in(page.text)
    old_session = b.cookies["session"]
    assert b.post("/logout", data={"csrf_token": stale_token}).status_code == 303
    # the other tab still holds the old form: CSRF token was rotated at logout, so it is refused politely
    r = b.post(f"/classes/{ids['c1']}/book", data={"csrf_token": stale_token})
    assert r.status_code == 403 and "expired" in r.text.lower()
    # a replay with the old session cookie and a freshly valid token: the session is gone
    replay = AppBrowser(world.app)
    replay.cookies.set("session", old_session)
    assert replay.post_form(f"/classes/{ids['c1']}/book").status_code == 303
    assert one(world.path, "SELECT COUNT(*) FROM bookings WHERE user_id=?", ids["b"]) == 0


def test_every_signed_in_page_is_no_store_so_the_back_button_cannot_show_private_data(world):
    ids = world.ids
    for who, paths in (("a", ["/", f"/classes/{ids['c1']}", "/my-bookings", "/login", "/signup"]),
                       ("admin", ["/", "/admin/classes", "/admin/classes/new", f"/admin/classes/{ids['c1']}",
                                  f"/admin/classes/{ids['c1']}/edit"])):
        b = world.browser(who)
        for p in paths:
            assert b.get(p).headers.get("cache-control") == "no-store", (who, p)
    b = world.browser("a")
    page = b.get("/my-bookings")
    r = b.post(f"/bookings/{ids['booking_a']}/cancel", data={"csrf_token": csrf_in(page.text)})
    assert r.headers.get("cache-control") in (None, "no-store")  # redirects carry no page content


def test_visiting_a_private_page_signed_out_then_signing_in_lands_back_there(world):
    with db.write_tx(world.path) as conn:
        insert_user(conn, "back@example.com", "Back", password=PASSWORD)
    b = AppBrowser(world.app)
    r = b.get("/my-bookings")
    assert r.status_code == 303 and r.headers["location"] == "/login?next=/my-bookings"
    page = b.get(r.headers["location"])
    r = b.post("/login", data={"csrf_token": csrf_in(page.text), "email": "back@example.com", "password": PASSWORD,
                               "next": "/my-bookings"})
    assert r.status_code == 303 and r.headers["location"] == "/my-bookings"
    assert b.get("/my-bookings").status_code == 200


def test_a_student_who_follows_an_admin_link_after_signing_in_gets_a_clear_refusal(world):
    b = world.browser("a")
    r = b.get("/admin/classes")
    assert r.status_code == 403 and "do not have permission" in r.text and 'href="/"' in r.text
