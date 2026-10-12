"""T4: schedule, class page and admin class management (roles come from dependency overrides + fixture rows)."""
import re
from pathlib import Path
import threading
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from classbook.app import create_app
from classbook.kernel import db, rules
from classbook.kernel.timeutil import FixedClock, to_text
from classbook.web.deps import User, current_user
from tests.conftest import add_booking, add_class, add_user

NOW = datetime(2026, 10, 10, 12, 0, 0, tzinfo=timezone.utc)
TOKEN = "T" * 43
ADMIN = User(1, "maya@example.com", "Maya", "admin")
STUDENT = User(2, "sam@example.com", "Sam", "student")


def at(**delta):
    return to_text(NOW + timedelta(**delta))


@pytest.fixture
def clock():
    return FixedClock(NOW)


@pytest.fixture
def app(settings, clock):
    app = create_app(settings, clock)
    app.state.role = None
    app.dependency_overrides[current_user] = lambda: app.state.role
    return app


@pytest.fixture
def seeded(app, settings):
    """users 1 (admin, from bootstrap) and 2 (student) exist as rows; helpers insert classes/bookings."""
    with db.write_tx(settings.database_path) as c:
        # the admin row (id 1, maya@example.com) is created by the T3 bootstrap at app start
        c.execute("UPDATE users SET prev_login_at = '2026-10-09T08:00:00Z' WHERE id = 1")
        c.execute("INSERT INTO users (id, email, name, password_hash, role, created_at) VALUES "
                  "(2, 'sam@example.com', 'Sam <b>', 'x', 'student', '2026-01-01T00:00:00Z')")
    return settings.database_path


def make(path, **kw):
    with db.write_tx(path) as c:
        cid = add_class(c, **kw)
    return cid


def book(path, cid, uid=2):
    with db.write_tx(path) as c:
        return add_booking(c, cid, uid)


def client_as(app, user):
    app.state.role = user
    return TestClient(app, follow_redirects=False)


def post(client, path, data=None):
    client.cookies.set("csrf", TOKEN)
    return client.post(path, data={"csrf_token": TOKEN, **(data or {})})


def rows(path, sql, *args):
    with db.read_conn(path) as c:
        return c.execute(sql, args).fetchall()


GOOD = {"title": "Evening Flow", "starts_at": "2026-10-20T18:30", "duration_min": "60", "instructor": "Maya",
        "capacity": "8"}


# ---- schedule (US-1) ----------------------------------------------------------------------------------------
def test_schedule_lists_in_start_order_with_all_fields(app, seeded):
    make(seeded, starts=at(days=3), capacity=5)
    with db.write_tx(seeded) as c:
        c.execute("INSERT INTO classes (title, starts_at, duration_min, instructor, capacity, created_at) VALUES "
                  "('Early', ?, 45, 'Bo', 3, 'x')", (at(days=1),))
    html = client_as(app, None).get("/").text
    assert html.index("Early") < html.index("Flow")
    assert "45 min" in html and "with Bo" in html and "5 spots left" in html


def test_schedule_empty_message(app, seeded):
    assert "No classes are scheduled yet" in client_as(app, None).get("/").text


def test_schedule_hides_started_cancelled_and_beyond_60_days(app, seeded):
    make(seeded, starts=at(seconds=-1))
    make(seeded, starts=at(days=2), status="cancelled")
    make(seeded, starts=at(days=60, seconds=1))
    assert "No classes are scheduled yet" in client_as(app, None).get("/").text


def test_full_class_shows_full_and_no_book_action(app, seeded):
    cid = make(seeded, starts=at(days=2), capacity=1)
    with db.write_tx(seeded) as c:
        add_booking(c, cid, add_user(c, "other@example.com"))
    html = client_as(app, None).get("/").text
    assert "<strong>Full</strong>" in html and "View and book" not in html
    assert "<strong>Full</strong>" in client_as(app, STUDENT).get(f"/classes/{cid}").text
    assert "<form" not in client_as(app, STUDENT).get(f"/classes/{cid}").text.split('class="booking"')[1].split("</div>")[0]


@pytest.mark.parametrize("delta", [timedelta(days=30) - timedelta(seconds=1), timedelta(days=30),
                                   timedelta(days=30, seconds=1), timedelta(days=60), timedelta(days=60, seconds=1)])
def test_day_30_and_60_edges_agree_with_is_bookable(app, seeded, delta):
    cid = make(seeded, starts=to_text(NOW + delta))
    row = {"starts_at": to_text(NOW + delta), "status": "active"}
    html = client_as(app, STUDENT).get("/").text
    listed = f'href="/classes/{cid}"' in html
    assert listed == rules.is_listed(row, NOW)
    if listed:
        state = re.search(r'data-state="(\w+)"', html).group(1)
        assert (state == "bookable") == rules.is_bookable(row, NOW)
        page = client_as(app, STUDENT).get(f"/classes/{cid}").text
        assert ("<form" in page.split('class="booking"')[1]) == rules.is_bookable(row, NOW)


def test_beyond_30_days_is_greyed_with_london_opens_date_and_no_action(app, seeded):
    make(seeded, starts="2026-11-20T18:30:00Z")  # opens 30x24h earlier = 21 Oct 18:30 UTC = 19:30 BST in London
    html = client_as(app, None).get("/").text
    assert 'data-state="opens_later"' in html and "greyed" in html
    assert "Opens for booking on Wed 21 Oct 2026, 19:30" in html
    assert "View and book" not in html


def test_class_becomes_bookable_as_time_passes_without_admin_action(app, seeded, clock):
    cid = make(seeded, starts=at(days=31))
    assert "Opens for booking on" in client_as(app, STUDENT).get(f"/classes/{cid}").text
    clock.advance(days=1, seconds=1)
    page = client_as(app, STUDENT).get(f"/classes/{cid}").text
    assert "Opens for booking" not in page and f'action="/classes/{cid}/book"' in page


# ---- class page (AC-2.3) ----------------------------------------------------------------------------------
def test_visitor_gets_sign_in_link_with_next(app, seeded):
    cid = make(seeded, starts=at(days=2))
    page = client_as(app, None).get(f"/classes/{cid}")
    assert f'href="/login?next=/classes/{cid}"' in page.text and "Sign in to book" in page.text
    assert page.headers["cache-control"] == "no-store"


def test_student_sees_book_form_with_csrf_and_admin_sees_manage_link(app, seeded):
    cid = make(seeded, starts=at(days=2))
    page = client_as(app, STUDENT).get(f"/classes/{cid}").text
    assert f'action="/classes/{cid}/book"' in page and 'name="csrf_token"' in page
    admin = client_as(app, ADMIN).get(f"/classes/{cid}").text
    assert f'href="/admin/classes/{cid}"' in admin and "Book</button>" not in admin


def test_class_page_states_and_404(app, seeded):
    cancelled = make(seeded, starts=at(days=2), status="cancelled")
    started = make(seeded, starts=at(seconds=-5))
    c = client_as(app, STUDENT)
    assert "cancelled by the studio" in c.get(f"/classes/{cancelled}").text
    assert "already started" in c.get(f"/classes/{started}").text
    assert c.get("/classes/9999").status_code == 404
    booked = make(seeded, starts=at(days=2))
    book(seeded, booked)
    assert "You are booked" in c.get(f"/classes/{booked}").text


def test_titles_and_instructor_are_escaped(app, seeded):
    with db.write_tx(seeded) as c:
        cid = c.execute("INSERT INTO classes (title, starts_at, duration_min, instructor, capacity, created_at) VALUES "
                        "('<script>alert(1)</script>', ?, 60, '<img src=x onerror=alert(2)>', 5, 'x')",
                        (at(days=2),)).lastrowid
    book(seeded, cid)
    for who, path in ((None, "/"), (None, f"/classes/{cid}"), (ADMIN, "/admin/classes"), (ADMIN, f"/admin/classes/{cid}"),
                      (ADMIN, f"/admin/classes/{cid}/edit")):
        html = client_as(app, who).get(path).text
        assert "<script>alert" not in html and "<img src=x" not in html, path
        assert "&lt;" in html or "&#34;" in html or "&lt;script" in html, path
    assert "Sam &lt;b&gt;" in client_as(app, ADMIN).get(f"/admin/classes/{cid}").text  # student name in roster


# ---- roles ---------------------------------------------------------------------------------------------------
ADMIN_ROUTES = [("get", "/admin/classes"), ("get", "/admin/classes/new"), ("post", "/admin/classes"),
                ("get", "/admin/classes/1"), ("get", "/admin/classes/1/edit"), ("post", "/admin/classes/1"),
                ("post", "/admin/classes/1/cancel")]


@pytest.mark.parametrize("method,path", ADMIN_ROUTES)
def test_student_is_denied_and_visitor_sent_to_login(app, seeded, method, path):
    make(seeded, starts=at(days=2))
    for who, code in ((STUDENT, 403), (None, 303)):
        c = client_as(app, who)
        r = c.get(path) if method == "get" else post(c, path, GOOD)
        assert r.status_code == code, (who, path)
    assert rows(seeded, "SELECT COUNT(*) FROM classes")[0][0] == 1  # nothing created or changed
    assert rows(seeded, "SELECT status FROM classes")[0][0] == "active"
    if method == "get":
        assert client_as(app, None).get(path).headers["location"].startswith("/login?next=/admin/classes")


def test_admin_post_without_csrf_is_403(app, seeded):
    assert client_as(app, ADMIN).post("/admin/classes", data=GOOD).status_code == 403


# ---- create / validation (AC-5.x) ----------------------------------------------------------------------------
def test_admin_creates_class_all_spots_free_and_stores_utc(app, seeded):
    c = client_as(app, ADMIN)
    r = post(c, "/admin/classes", GOOD)
    assert r.status_code == 303 and r.headers["location"].startswith("/admin/classes/")
    row = rows(seeded, "SELECT * FROM classes")[0]
    assert row["starts_at"] == "2026-10-20T17:30:00Z" and row["capacity"] == 8 and row["status"] == "active"
    assert "Evening Flow" in client_as(app, None).get("/").text and "8 spots left" in client_as(app, None).get("/").text


@pytest.mark.parametrize("field,value,msg", [
    ("title", "   ", "required"), ("title", "a\nb", "not allowed"), ("capacity", "0", "between"),
    ("capacity", "-2", "between"), ("capacity", "abc", "whole number"), ("capacity", "201", "between"),
    ("duration_min", "4", "between"), ("instructor", "", "required"), ("starts_at", "", "date and time"),
    ("starts_at", "2026-10-09T10:00", "future"), ("starts_at", "2026-10-10T13:00", "future"),
    ("starts_at", "2027-03-28T01:30", "does not exist"),  # spring-forward gap, rejected by the kernel
])
def test_invalid_fields_are_rejected_per_field_and_nothing_saved(app, seeded, field, value, msg):
    r = post(client_as(app, ADMIN), "/admin/classes", {**GOOD, field: value})
    assert r.status_code == 422 and msg in r.text
    assert f'id="e-{field}"' in r.text and rows(seeded, "SELECT COUNT(*) FROM classes")[0][0] == 0


def test_start_exactly_now_is_rejected_and_one_second_ahead_accepted(app, seeded):
    c = client_as(app, ADMIN)
    assert post(c, "/admin/classes", {**GOOD, "starts_at": "2026-10-10T13:00"}).status_code == 422  # 12:00Z = 13:00 BST
    assert post(c, "/admin/classes", {**GOOD, "starts_at": "2026-10-10T13:01"}).status_code == 303


def test_autumn_fold_takes_first_occurrence(app, seeded):
    post(client_as(app, ADMIN), "/admin/classes", {**GOOD, "starts_at": "2026-10-25T01:30"})
    assert rows(seeded, "SELECT starts_at FROM classes")[0][0] == "2026-10-25T00:30:00Z"


# ---- admin list / detail / roster ---------------------------------------------------------------------------
def test_admin_list_has_all_classes_and_last_signin(app, seeded):
    make(seeded, starts=at(days=-3))
    make(seeded, starts=at(days=2), status="cancelled")
    make(seeded, starts=at(days=70))
    html = client_as(app, ADMIN).get("/admin/classes").text
    assert html.count('href="/admin/classes/') >= 3 and "Cancelled" in html and "Past" in html
    assert "previous sign-in: Fri 09 Oct 2026, 09:00" in html


def test_admin_detail_shows_roster_and_spots_left(app, seeded):
    cid = make(seeded, starts=at(days=2), capacity=3)
    book(seeded, cid)
    html = client_as(app, ADMIN).get(f"/admin/classes/{cid}").text
    assert "sam@example.com" in html and "spots left 2" in html
    assert client_as(app, ADMIN).get("/admin/classes/999").status_code == 404


# ---- edit -----------------------------------------------------------------------------------------------------
def test_edit_prefills_in_london_time_and_saves(app, seeded):
    cid = make(seeded, starts="2026-11-01T10:00:00Z", capacity=4)
    c = client_as(app, ADMIN)
    assert 'value="2026-11-01T10:00"' in c.get(f"/admin/classes/{cid}/edit").text
    r = post(c, f"/admin/classes/{cid}", {**GOOD, "starts_at": "2026-11-02T09:00", "capacity": "6"})
    assert r.status_code == 303
    row = rows(seeded, "SELECT * FROM classes")[0]
    assert (row["starts_at"], row["capacity"], row["title"]) == ("2026-11-02T09:00:00Z", 6, "Evening Flow")


def test_edit_into_the_past_or_gap_is_rejected(app, seeded):
    cid = make(seeded, starts=at(days=5))
    c = client_as(app, ADMIN)
    assert post(c, f"/admin/classes/{cid}", {**GOOD, "starts_at": "2026-10-10T08:00"}).status_code == 422
    assert post(c, f"/admin/classes/{cid}", {**GOOD, "starts_at": "2027-03-28T01:30"}).status_code == 422
    assert rows(seeded, "SELECT starts_at FROM classes")[0][0] == at(days=5)


def test_cannot_edit_cancelled_or_started_class(app, seeded):
    a = make(seeded, starts=at(days=2), status="cancelled")
    b = make(seeded, starts=at(seconds=-1))
    c = client_as(app, ADMIN)
    for cid in (a, b):
        assert c.get(f"/admin/classes/{cid}/edit").status_code == 409
        assert post(c, f"/admin/classes/{cid}", GOOD).status_code == 409
    assert post(c, "/admin/classes/999", GOOD).status_code == 404


def test_lowering_capacity_below_booked_is_refused_but_equal_is_fine(app, seeded):
    cid = make(seeded, starts=at(days=5), capacity=5)
    book(seeded, cid)
    with db.write_tx(seeded) as c:
        add_booking(c, cid, add_user(c, "t@example.com"))
    c = client_as(app, ADMIN)
    r = post(c, f"/admin/classes/{cid}", {**GOOD, "starts_at": "2026-10-20T18:30", "capacity": "1"})
    assert r.status_code == 409 and "capacity cannot go below 2" in r.text
    assert rows(seeded, "SELECT capacity FROM classes")[0][0] == 5
    assert post(c, f"/admin/classes/{cid}", {**GOOD, "capacity": "2"}).status_code == 303


def test_capacity_lowering_waits_for_a_booking_in_flight_then_refuses(app, seeded):
    """The check and the update share one write lock: a booking committed first must be counted."""
    cid = make(seeded, starts=at(days=5), capacity=10)
    for _ in range(3):
        with db.write_tx(seeded) as c:
            add_booking(c, cid, add_user(c, f"u{_}@example.com"))
    holding, release, result = threading.Event(), threading.Event(), {}

    def booker():  # a booking transaction that has taken the lock and counts to 4 booked
        with db.write_tx(seeded) as c:
            holding.set()
            release.wait(5)
            add_booking(c, cid, add_user(c, "late@example.com"))

    def editor():
        result["r"] = post(client_as(app, ADMIN), f"/admin/classes/{cid}", {**GOOD, "capacity": "3"})

    t1 = threading.Thread(target=booker); t1.start(); holding.wait(5)
    t2 = threading.Thread(target=editor); t2.start()
    t2.join(0.4)
    assert t2.is_alive()  # blocked on the lock, not racing past it
    release.set(); t1.join(); t2.join()
    assert result["r"].status_code == 409
    assert rows(seeded, "SELECT capacity FROM classes")[0][0] == 10


def test_capacity_never_ends_below_booked_under_many_races(app, seeded):
    cid = make(seeded, starts=at(days=5), capacity=10)
    ids = []
    with db.write_tx(seeded) as c:
        ids = [add_user(c, f"r{i}@example.com") for i in range(8)]

    def booker(uid):
        with db.write_tx(seeded) as c:  # same shape as T5: count and insert under one lock
            if rules.spots_left(c, cid) > 0:
                add_booking(c, cid, uid)

    threads = [threading.Thread(target=booker, args=(u,)) for u in ids]
    threads.append(threading.Thread(target=lambda: post(client_as(app, ADMIN), f"/admin/classes/{cid}", {**GOOD, "capacity": "4"})))
    for t in threads: t.start()
    for t in threads: t.join()
    cap, booked = rows(seeded, "SELECT c.capacity, (SELECT COUNT(*) FROM bookings WHERE status='booked') FROM classes c")[0]
    assert booked <= cap


# ---- cancel (AC-6.3) ------------------------------------------------------------------------------------------
def test_cancel_marks_class_and_bookings_cancelled_by_studio(app, seeded):
    cid = make(seeded, starts=at(days=2))
    other = make(seeded, starts=at(days=3))
    keep = book(seeded, other)
    book(seeded, cid)
    with db.write_tx(seeded) as c:
        gone = add_booking(c, cid, add_user(c, "x@example.com"), status="cancelled")  # student-cancelled stays so
    r = post(client_as(app, ADMIN), f"/admin/classes/{cid}/cancel")
    assert r.status_code == 303
    assert rows(seeded, "SELECT status FROM classes WHERE id=?", cid)[0][0] == "cancelled"
    got = {r["id"]: (r["status"], r["cancelled_by"], r["cancelled_at"]) for r in rows(seeded, "SELECT * FROM bookings")}
    assert got[gone][1] == "student" and got[keep] == ("booked", None, None)
    studio = [v for v in got.values() if v[1] == "studio"]
    assert len(studio) == 1 and studio[0] == ("cancelled", "studio", to_text(NOW))
    assert rows(seeded, "SELECT COUNT(*) FROM messages")[0][0] == 0  # no emails
    assert 'href="/classes/%d"' % cid not in client_as(app, None).get("/").text


def test_cancel_twice_is_a_no_op(app, seeded):
    cid = make(seeded, starts=at(days=2))
    book(seeded, cid)
    c = client_as(app, ADMIN)
    post(c, f"/admin/classes/{cid}/cancel")
    first = rows(seeded, "SELECT cancelled_at FROM bookings")[0][0]
    app.state.clock = FixedClock(NOW + timedelta(hours=1))
    assert post(c, f"/admin/classes/{cid}/cancel").status_code == 303
    assert rows(seeded, "SELECT cancelled_at FROM bookings")[0][0] == first
    assert post(c, "/admin/classes/999/cancel").status_code == 404


def test_cancel_is_atomic_if_the_booking_update_fails(app, seeded):
    cid = make(seeded, starts=at(days=2))
    book(seeded, cid)
    with db.write_tx(seeded) as c:  # make the second statement blow up
        c.execute("CREATE TRIGGER boom BEFORE UPDATE ON bookings BEGIN SELECT RAISE(ABORT, 'boom'); END")
    c = TestClient(app, follow_redirects=False, raise_server_exceptions=False)
    app.state.role = ADMIN
    assert post(c, f"/admin/classes/{cid}/cancel").status_code == 500
    assert rows(seeded, "SELECT status FROM classes")[0][0] == "active"
    assert rows(seeded, "SELECT status, cancelled_by FROM bookings")[0][:] == ("booked", None)


def test_busy_database_answers_503(app, seeded, monkeypatch):
    cid = make(seeded, starts=at(days=2))
    real = db.write_tx  # short lock timeout so the test is quick
    monkeypatch.setattr(db, "write_tx", lambda p: real(p, 50))
    with real(seeded):
        r = post(client_as(app, ADMIN), f"/admin/classes/{cid}/cancel")
    assert r.status_code == 503


# ---- review round 1 -------------------------------------------------------------------------------------------
def test_roster_lists_only_booked_students(app, seeded):
    cid = make(seeded, starts=at(days=2), capacity=5)
    with db.write_tx(seeded) as c:
        gone = add_user(c, "gone@example.com")
        add_booking(c, cid, gone, status="cancelled")
    book(seeded, cid)
    html = client_as(app, ADMIN).get(f"/admin/classes/{cid}").text
    assert "sam@example.com" in html and "gone@example.com" not in html
    assert "booked 1" in html and "spots left 4" in html
    post(client_as(app, ADMIN), f"/admin/classes/{cid}/cancel")  # after a class cancel nobody is booked
    html = client_as(app, ADMIN).get(f"/admin/classes/{cid}").text
    assert "sam@example.com" not in html and "gone@example.com" not in html and "Nobody is booked" in html


HUGE = "99999999999999999999999"


@pytest.mark.parametrize("path", [f"/classes/{HUGE}", f"/admin/classes/{HUGE}", f"/admin/classes/{HUGE}/edit"])
def test_huge_class_id_is_404_not_500(app, seeded, path):
    assert client_as(app, ADMIN).get(path).status_code == 404
    assert post(client_as(app, ADMIN), f"/admin/classes/{HUGE}/cancel").status_code == 404
    assert post(client_as(app, ADMIN), f"/admin/classes/{HUGE}", GOOD).status_code == 404


def test_cancelling_a_started_class_is_refused_and_button_hidden(app, seeded):
    cid = make(seeded, starts=at(hours=-1))
    book(seeded, cid)
    c = client_as(app, ADMIN)
    assert "Cancel this class" not in c.get(f"/admin/classes/{cid}").text
    r = post(c, f"/admin/classes/{cid}/cancel")
    assert r.status_code == 409 and "already started" in r.text
    assert rows(seeded, "SELECT status FROM classes")[0][0] == "active"
    assert rows(seeded, "SELECT status, cancelled_by FROM bookings")[0][:] == ("booked", None)
    future = make(seeded, starts=at(days=1))
    assert "Cancel this class" in c.get(f"/admin/classes/{future}").text


def test_second_cancel_says_already_cancelled(app, seeded):
    cid = make(seeded, starts=at(days=2))
    c = client_as(app, ADMIN)
    post(c, f"/admin/classes/{cid}/cancel")
    assert "Class cancelled." in c.get(f"/admin/classes/{cid}").text
    post(c, f"/admin/classes/{cid}/cancel")
    assert "That class was already cancelled." in c.get(f"/admin/classes/{cid}").text


def test_capacity_error_is_shown_beside_other_field_errors(app, seeded):
    cid = make(seeded, starts=at(days=5), capacity=5)
    book(seeded, cid)
    with db.write_tx(seeded) as c:
        add_booking(c, cid, add_user(c, "t@example.com"))
    r = post(client_as(app, ADMIN), f"/admin/classes/{cid}", {**GOOD, "title": " ", "capacity": "1"})
    assert r.status_code == 422 and 'id="e-capacity"' in r.text and 'id="e-title"' in r.text


def _lum(hex_):
    ch = [int(hex_[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    ch = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in ch]
    return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]


def test_greyed_text_meets_wcag_aa_contrast_in_light_and_dark():
    css = (Path(__file__).parent.parent / "classbook/web/static/style.css").read_text()
    greyed = re.search(r"\.class\.greyed\s*\{([^}]*)\}", css).group(1)
    assert "opacity" not in greyed  # grey by colour only; opacity would lower contrast below AA
    light, dark = css.splitlines()[0], css.splitlines()[1]
    for block, bg in ((light, "#ffffff"), (dark, re.search(r"--bg:(#[0-9a-fA-F]{6})", dark).group(1))):
        fg = re.search(r"--muted:\s*(#[0-9a-fA-F]{6})", block).group(1)
        hi, lo = sorted((_lum(fg), _lum(bg)), reverse=True)
        assert (hi + 0.05) / (lo + 0.05) >= 4.5, (fg, bg)
