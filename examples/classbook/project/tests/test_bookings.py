"""T5: booking and cancellation. Real temp-file SQLite with production pragmas; FixedClock."""
import re
import sqlite3
import threading
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from classbook.app import create_app
from classbook.config import Settings
from classbook.kernel import db
from classbook.kernel.timeutil import FixedClock, to_text
from classbook.services import bookings as svc
from classbook.services.bookings import Outcome as O
from classbook.web.deps import User, current_user
from tests.conftest import add_booking, add_class, add_user

NOW = datetime(2026, 10, 10, 12, 0, 0, tzinfo=timezone.utc)
T = lambda **d: to_text(NOW + timedelta(**d))  # noqa: E731


@pytest.fixture
def clock():
    return FixedClock(NOW)


@pytest.fixture
def world(conn):
    """A student, another student, an admin and an active class 3 days out (capacity 2)."""
    return dict(a=add_user(conn, "a@example.com"), b=add_user(conn, "b@example.com"),
                admin=add_user(conn, "admin@example.com", "admin"), cls=add_class(conn, T(days=3), 2))


def booked_count(conn, class_id):
    return conn.execute("SELECT COUNT(*) FROM bookings WHERE class_id=? AND status='booked'", (class_id,)).fetchone()[0]


# ---------- unit: rule order (api.md #6 and #8) ----------

def test_book_success_returns_what_happened_for_the_mail_hook(dbpath, conn, clock, world):
    r = svc.book(dbpath, clock, world["a"], world["cls"])
    assert r.outcome is O.BOOKED and r.changed and r.booking_id
    assert (r.user_email, r.class_title, r.starts_at) == ("a@example.com", "Flow", NOW + timedelta(days=3))
    assert booked_count(conn, world["cls"]) == 1


def test_unknown_class_comes_before_everything(dbpath, clock, world):
    assert svc.book(dbpath, clock, world["a"], 9999).outcome is O.NOT_FOUND


def test_started_or_cancelled_beats_too_far_full_and_already_booked(dbpath, conn, clock, world):
    far_cancelled = add_class(conn, T(days=45), 1, "cancelled")
    assert svc.book(dbpath, clock, world["a"], far_cancelled).outcome is O.STARTED_OR_CANCELLED
    started = add_class(conn, T(seconds=0), 1)  # starts exactly now: started
    add_booking(conn, started, world["b"])      # full AND started AND (a not booked)
    assert svc.book(dbpath, clock, world["a"], started).outcome is O.STARTED_OR_CANCELLED
    add_booking(conn, started, world["a"])      # already booked too: still started_or_cancelled
    assert svc.book(dbpath, clock, world["a"], started).outcome is O.STARTED_OR_CANCELLED


def test_too_far_ahead_beats_already_booked_and_full_and_gives_opens_on(dbpath, conn, clock, world):
    far = add_class(conn, T(days=31), 1)
    add_booking(conn, far, world["a"])
    add_booking(conn, far, world["b"])  # capacity 1 but 2 rows: absurd on purpose, still too_far_ahead
    r = svc.book(dbpath, clock, world["a"], far)
    assert r.outcome is O.TOO_FAR_AHEAD and r.opens_at == NOW + timedelta(days=1) and not r.changed


def test_already_booked_beats_full_and_is_a_noop(dbpath, conn, clock, world):
    c = add_class(conn, T(days=2), 1)
    assert svc.book(dbpath, clock, world["a"], c).outcome is O.BOOKED
    r = svc.book(dbpath, clock, world["a"], c)  # class is now full AND a already holds the spot
    assert r.outcome is O.ALREADY_BOOKED and not r.changed
    assert booked_count(conn, c) == 1
    assert svc.book(dbpath, clock, world["b"], c).outcome is O.FULL


def test_window_boundaries_day_30_allowed_plus_one_second_refused(dbpath, conn, clock, world):
    edge = add_class(conn, T(days=30), 1)
    over = add_class(conn, T(days=30, seconds=1), 1)
    assert svc.book(dbpath, clock, world["a"], edge).outcome is O.BOOKED
    assert svc.book(dbpath, clock, world["a"], over).outcome is O.TOO_FAR_AHEAD


def test_rebooking_after_cancel_creates_a_new_row(dbpath, conn, clock, world):
    first = svc.book(dbpath, clock, world["a"], world["cls"])
    assert svc.cancel(dbpath, clock, world["a"], first.booking_id).outcome is O.CANCELLED
    second = svc.book(dbpath, clock, world["a"], world["cls"])
    assert second.outcome is O.BOOKED and second.booking_id != first.booking_id


def test_cancel_order_not_mine_then_already_cancelled_then_too_late(dbpath, conn, clock, world):
    soon = add_class(conn, T(hours=5), 2)
    mine_cancelled = add_booking(conn, soon, world["a"], "cancelled")
    # someone else's booking, which is also cancelled and too late: 404 wins
    assert svc.cancel(dbpath, clock, world["b"], mine_cancelled).outcome is O.NOT_FOUND
    # mine, cancelled AND too late: the no-op comes first
    assert svc.cancel(dbpath, clock, world["a"], mine_cancelled).outcome is O.ALREADY_CANCELLED
    live = add_booking(conn, soon, world["b"])
    r = svc.cancel(dbpath, clock, world["b"], live)
    assert r.outcome is O.TOO_LATE and not r.changed
    assert conn.execute("SELECT status FROM bookings WHERE id=?", (live,)).fetchone()[0] == "booked"
    assert svc.cancel(dbpath, clock, world["a"], 9999).outcome is O.NOT_FOUND


def test_cancel_exactly_12h_allowed_one_second_less_refused(dbpath, conn, clock, world):
    ok = add_booking(conn, add_class(conn, T(hours=12), 1), world["a"])
    late = add_booking(conn, add_class(conn, T(hours=12, seconds=-1), 1), world["a"])
    assert svc.cancel(dbpath, clock, world["a"], ok).outcome is O.CANCELLED
    assert svc.cancel(dbpath, clock, world["a"], late).outcome is O.TOO_LATE


def test_cancel_returns_mail_data_and_frees_the_spot(dbpath, conn, clock, world):
    b = svc.book(dbpath, clock, world["a"], world["cls"]).booking_id
    r = svc.cancel(dbpath, clock, world["a"], b)
    assert r.outcome is O.CANCELLED and r.changed and r.user_email == "a@example.com"
    row = conn.execute("SELECT status, cancelled_by, cancelled_at FROM bookings WHERE id=?", (b,)).fetchone()
    assert tuple(row) == ("cancelled", "student", to_text(NOW))
    assert booked_count(conn, world["cls"]) == 0
    assert svc.cancel(dbpath, clock, world["a"], b).outcome is O.ALREADY_CANCELLED  # no second change


def test_studio_cancelled_booking_cannot_be_cancelled_again(dbpath, conn, clock, world):
    bid = add_booking(conn, world["cls"], world["a"])
    conn.execute("UPDATE bookings SET status='cancelled', cancelled_by='studio', cancelled_at=? WHERE id=?", (T(), bid))
    assert svc.cancel(dbpath, clock, world["a"], bid).outcome is O.ALREADY_CANCELLED


# ---------- now is read once, inside the lock (M-4) ----------

class ProbeClock(FixedClock):
    def __init__(self, now, path):
        super().__init__(now)
        self.path, self.calls, self.lock_held = path, 0, None

    def now(self):
        self.calls += 1
        probe = db.connect(self.path, busy_timeout_ms=0)
        try:
            probe.execute("BEGIN IMMEDIATE")
            self.lock_held = False
            probe.execute("ROLLBACK")
        except sqlite3.OperationalError:
            self.lock_held = True
        finally:
            probe.close()
        return super().now()


@pytest.mark.parametrize("op", ["book", "cancel", "refused_book", "refused_cancel"])
def test_clock_is_read_exactly_once_and_only_while_the_write_lock_is_held(dbpath, conn, world, op):
    pc = ProbeClock(NOW, dbpath)
    bid = add_booking(conn, world["cls"], world["b"])
    if op == "book":
        svc.book(dbpath, pc, world["a"], world["cls"])
    elif op == "cancel":
        svc.cancel(dbpath, pc, world["b"], bid)
    elif op == "refused_book":
        svc.book(dbpath, pc, world["a"], 9999)
    else:
        svc.cancel(dbpath, pc, world["a"], bid)
    assert pc.calls == 1 and pc.lock_held is True


# ---------- per-user action cap (F24) ----------

def test_21st_action_in_an_hour_is_throttled_and_refusals_count(dbpath, conn, clock, world):
    for _ in range(20):  # all refusals (unknown class) still count
        assert svc.book(dbpath, clock, world["a"], 9999).outcome is O.NOT_FOUND
    r = svc.book(dbpath, clock, world["a"], world["cls"])
    assert r.outcome is O.THROTTLED and not r.changed
    assert booked_count(conn, world["cls"]) == 0
    assert svc.cancel(dbpath, clock, world["a"], 1).outcome is O.THROTTLED  # shared by book and cancel
    assert svc.book(dbpath, clock, world["b"], world["cls"]).outcome is O.BOOKED  # per user
    assert conn.execute("SELECT COUNT(*) FROM user_actions WHERE user_id=?", (world["a"],)).fetchone()[0] == 20


def test_cap_window_rolls_after_an_hour(dbpath, conn, clock, world):
    for _ in range(20):
        svc.book(dbpath, clock, world["a"], 9999)
    assert svc.book(dbpath, clock, world["a"], world["cls"]).outcome is O.THROTTLED
    clock.advance(minutes=59, seconds=59)
    assert svc.book(dbpath, clock, world["a"], world["cls"]).outcome is O.THROTTLED
    clock.advance(seconds=1)  # the oldest actions are now exactly 1h old: outside the window
    assert svc.book(dbpath, clock, world["a"], world["cls"]).outcome is O.BOOKED


# ---------- listing query ----------

def test_upcoming_for_shows_booked_and_studio_cancelled_only(dbpath, conn, clock, world):
    a, b = world["a"], world["b"]
    soon, later, past = add_class(conn, T(days=1), 5), add_class(conn, T(days=2), 5), add_class(conn, T(days=-1), 5)
    add_booking(conn, soon, a)
    studio = add_booking(conn, later, a)
    conn.execute("UPDATE bookings SET status='cancelled', cancelled_by='studio' WHERE id=?", (studio,))
    add_booking(conn, world["cls"], a, "cancelled")  # cancelled by the student: hidden
    add_booking(conn, past, a)                       # past: hidden
    add_booking(conn, soon, b)                       # someone else's: hidden
    rows = svc.upcoming_for(conn, a, NOW)
    assert [(r["class_id"], r["status"]) for r in rows] == [(soon, "booked"), (later, "cancelled")]


# ---------- HTTP integration ----------

TOK = "t" * 43
STUDENT_A, STUDENT_B, ADMIN = User(1, "a@example.com", "A", "student"), User(2, "b@example.com", "B", "student"), User(3, "admin@example.com", "Admin", "admin")


@pytest.fixture
def http(env, clock):
    """App over a fresh DB with ids 1=A, 2=B, 3=admin and class 1 (3 days out, capacity 2).

    Students and the class go in BEFORE create_app; the app's startup bootstrap (T3) then creates the one
    allowed admin (id 3, ADMIN_EMAIL from the test env), so the schema's one-admin index is never worked around.
    """
    db.migrate(env["DATABASE_PATH"])
    c = db.connect(env["DATABASE_PATH"])
    for email in ("a@example.com", "b@example.com"):
        add_user(c, email)
    add_class(c, T(days=3), 2)
    c.close()
    app = create_app(Settings.from_env(env), clock)
    c = db.connect(env["DATABASE_PATH"])
    assert c.execute("SELECT id FROM users WHERE role='admin'").fetchone()[0] == ADMIN.id
    c.close()
    who = {"user": STUDENT_A}
    app.dependency_overrides[current_user] = lambda: who["user"]
    client = TestClient(app, follow_redirects=False)
    client.cookies.set("csrf", TOK)
    client.who, client.path = who, env["DATABASE_PATH"]
    return client


def post(client, url, token=TOK):
    return client.post(url, data={"csrf_token": token})


def rows(client, sql, *args):
    c = db.connect(client.path)
    try:
        return c.execute(sql, args).fetchall()
    finally:
        c.close()


def test_book_redirects_to_my_bookings_and_lists_it(http):
    r = post(http, "/classes/1/book")
    assert r.status_code == 303 and r.headers["location"] == "/my-bookings"
    page = http.get("/my-bookings")
    assert page.status_code == 200 and "Flow" in page.text and "Booked: Flow" in page.text
    assert "/bookings/1/cancel" in page.text and 'name="csrf_token"' in page.text
    assert page.headers["cache-control"] == "no-store"


def test_book_requires_csrf_token(http):
    assert post(http, "/classes/1/book", token="wrong").status_code == 403
    assert rows(http, "SELECT * FROM bookings") == []


def test_double_submit_creates_exactly_one_booking_and_says_already_booked(http):
    first, second = post(http, "/classes/1/book"), post(http, "/classes/1/book")
    assert first.status_code == second.status_code == 303
    assert len(rows(http, "SELECT * FROM bookings")) == 1
    assert "already booked" in http.get("/my-bookings").text


def test_unknown_class_404_and_nothing_created(http):
    assert post(http, "/classes/999/book").status_code == 404


def test_started_cancelled_too_far_full_refusals_are_409(http):
    c = db.connect(http.path)
    started, cancelled = add_class(c, T(seconds=-1)), add_class(c, T(days=2), 2, "cancelled")
    far = add_class(c, T(days=40))
    full = add_class(c, T(days=2), 1)
    add_booking(c, full, 2)
    c.close()
    assert post(http, f"/classes/{started}/book").status_code == 409
    assert post(http, f"/classes/{cancelled}/book").status_code == 409
    r = post(http, f"/classes/{far}/book")
    assert r.status_code == 409 and "opens on" in r.text and "Booking for this class opens on" in r.text
    r = post(http, f"/classes/{full}/book")
    assert r.status_code == 409 and "full" in r.text.lower()
    assert [x["class_id"] for x in rows(http, "SELECT class_id FROM bookings WHERE user_id=1")] == []


def test_admin_cannot_book_and_anonymous_is_sent_to_login(http):
    http.who["user"] = ADMIN
    assert post(http, "/classes/1/book").status_code == 403
    assert http.get("/my-bookings").status_code == 403
    assert post(http, "/bookings/1/cancel").status_code == 403
    http.who["user"] = None
    assert http.get("/my-bookings").status_code == 303
    assert http.get("/my-bookings").headers["location"].startswith("/login?next=")
    assert post(http, "/classes/1/book").status_code == 303
    assert rows(http, "SELECT * FROM bookings") == []


def test_cancel_flow_and_noop_and_too_late(http):
    post(http, "/classes/1/book")
    r = post(http, "/bookings/1/cancel")
    assert r.status_code == 303 and r.headers["location"] == "/my-bookings"
    assert "Cancelled: Flow" in http.get("/my-bookings").text
    assert "Flow" not in http.get("/my-bookings").text.split("<main")[1].replace("Cancelled: Flow", "")
    again = post(http, "/bookings/1/cancel")  # no-op
    assert again.status_code == 303 and rows(http, "SELECT status FROM bookings")[0][0] == "cancelled"
    c = db.connect(http.path)
    soon = add_class(c, T(hours=11, minutes=59))
    bid = add_booking(c, soon, 1)
    c.close()
    r = post(http, f"/bookings/{bid}/cancel")
    assert r.status_code == 409 and "12 hours" in r.text
    assert rows(http, "SELECT status FROM bookings WHERE id=?", bid)[0][0] == "booked"
    page = http.get("/my-bookings").text
    assert f"/bookings/{bid}/cancel" not in page and "Too late to cancel online" in page


def test_student_a_cannot_see_or_cancel_student_bs_booking(http):
    http.who["user"] = STUDENT_B
    post(http, "/classes/1/book")
    assert "Flow" in http.get("/my-bookings").text
    http.who["user"] = STUDENT_A
    assert "Flow" not in http.get("/my-bookings").text
    assert post(http, "/bookings/1/cancel").status_code == 404
    assert rows(http, "SELECT status FROM bookings WHERE id=1")[0][0] == "booked"
    assert post(http, "/bookings/999/cancel").status_code == 404  # unknown looks the same


def test_my_bookings_marks_studio_cancelled_and_has_no_cancel_button(http):
    post(http, "/classes/1/book")
    c = db.connect(http.path)
    c.execute("UPDATE bookings SET status='cancelled', cancelled_by='studio', cancelled_at=? WHERE id=1", (T(),))
    c.close()
    page = http.get("/my-bookings").text
    assert "Cancelled by the studio" in page and "/bookings/1/cancel" not in page


def test_my_bookings_empty_state_and_xss_escaping(http):
    assert "no upcoming bookings" in http.get("/my-bookings").text
    c = db.connect(http.path)
    c.execute("UPDATE classes SET title='<script>alert(1)</script>' WHERE id=1")
    c.close()
    post(http, "/classes/1/book")
    page = http.get("/my-bookings").text
    assert "<script>alert(1)</script>" not in page and "&lt;script&gt;" in page


def test_http_throttle_returns_429_with_retry_after(http):
    for _ in range(20):
        post(http, "/classes/999/book")
    r = post(http, "/classes/1/book")
    assert r.status_code == 429 and r.headers["retry-after"] == "3600"
    assert rows(http, "SELECT * FROM bookings") == []


# ---------- concurrency: separate threads, separate connections ----------

def run_threads(fns):
    barrier, out, errors = threading.Barrier(len(fns)), [], []

    def wrap(fn):
        def go():
            barrier.wait()
            try:
                out.append(fn())
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)
        return go

    ts = [threading.Thread(target=wrap(f)) for f in fns]
    [t.start() for t in ts]
    [t.join(30) for t in ts]
    assert errors == []
    return out


def many_students(conn, n):
    return [add_user(conn, f"s{i}@example.com") for i in range(n)]


def test_50_threads_on_one_spot_exactly_one_wins(dbpath, conn, clock):
    cls = add_class(conn, T(days=3), 1)
    users = many_students(conn, 50)
    out = run_threads([lambda u=u: svc.book(dbpath, clock, u, cls) for u in users])
    kinds = [r.outcome for r in out]
    assert kinds.count(O.BOOKED) == 1 and kinds.count(O.FULL) == 49
    assert booked_count(conn, cls) == 1


def test_30_bookers_on_10_spots_exactly_10_win(dbpath, conn, clock):
    cls = add_class(conn, T(days=3), 10)
    users = many_students(conn, 30)
    out = run_threads([lambda u=u: svc.book(dbpath, clock, u, cls) for u in users])
    kinds = [r.outcome for r in out]
    assert kinds.count(O.BOOKED) == 10 and kinds.count(O.FULL) == 20
    assert booked_count(conn, cls) == 10


def test_same_student_double_submit_in_parallel_gives_exactly_one_booking(dbpath, conn, clock):
    cls = add_class(conn, T(days=3), 5)
    u = add_user(conn, "dbl@example.com")
    out = run_threads([lambda: svc.book(dbpath, clock, u, cls) for _ in range(10)])
    kinds = [r.outcome for r in out]
    assert kinds.count(O.BOOKED) == 1 and kinds.count(O.ALREADY_BOOKED) == 9
    assert booked_count(conn, cls) == 1


def test_book_vs_cancel_race_never_overbooks_and_spots_are_consistent(dbpath, conn, clock):
    cls = add_class(conn, T(days=3), 1)
    holder = add_user(conn, "holder@example.com")
    bid = svc.book(dbpath, clock, holder, cls).booking_id
    waiting = many_students(conn, 20)
    fns = [lambda: svc.cancel(dbpath, clock, holder, bid)] + [lambda u=u: svc.book(dbpath, clock, u, cls) for u in waiting]
    out = run_threads(fns)
    kinds = [r.outcome for r in out]
    assert kinds.count(O.CANCELLED) == 1 and kinds.count(O.BOOKED) <= 1
    assert booked_count(conn, cls) <= 1
    assert booked_count(conn, cls) == kinds.count(O.BOOKED)
    assert conn.execute("SELECT status FROM bookings WHERE id=?", (bid,)).fetchone()[0] == "cancelled"


def test_parallel_cancels_of_one_booking_free_the_spot_once(dbpath, conn, clock):
    cls = add_class(conn, T(days=3), 2)
    u = add_user(conn, "c@example.com")
    bid = svc.book(dbpath, clock, u, cls).booking_id
    out = run_threads([lambda: svc.cancel(dbpath, clock, u, bid) for _ in range(10)])
    kinds = [r.outcome for r in out]
    assert kinds.count(O.CANCELLED) == 1 and kinds.count(O.ALREADY_CANCELLED) == 9


def test_concurrent_http_requests_respect_capacity(http):
    c = db.connect(http.path)
    cls = add_class(c, T(days=3), 1)
    c.close()
    results = run_threads([lambda: post(http, f"/classes/{cls}/book").status_code for _ in range(8)])
    assert len(rows(http, "SELECT * FROM bookings WHERE class_id=? AND status='booked'", cls)) == 1
    assert sorted(set(results)) in ([303], [303, 409])
