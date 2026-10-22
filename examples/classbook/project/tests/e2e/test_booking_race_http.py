"""T7 (3): the booking race over REAL HTTP (uvicorn process, SQLite with production pragmas).

The per-task race tests use threads and TestClient. These use many separate HTTP connections against the real
server, which is the situation Maya's "50 people booking when a popular class opens" actually creates.
"""
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from tests.e2e.conftest import seed_students, sign_in
from tests.qa.support import ADMIN_EMAIL, ADMIN_PASSWORD, insert_booking, one, rows


def hammer(server, tokens, calls):
    """Run calls[i](client) for every client at the same moment (barrier). Returns [(status, seconds, resp)]."""
    clients = []
    for tok in tokens:
        c = server.client()
        c.cookies.set("session", tok)
        clients.append(c)
    barrier = threading.Barrier(len(clients))

    def go(i):
        barrier.wait()
        t0 = time.perf_counter()
        resp = calls[i](clients[i])
        return resp.status_code, time.perf_counter() - t0, resp

    with ThreadPoolExecutor(max_workers=len(clients)) as pool:
        out = list(pool.map(go, range(len(clients))))
    for c in clients:
        c.close()
    return out


def no_server_errors(server):
    assert "Traceback" not in server.log and "unhandled exception" not in server.log, server.log[-2000:]


def mails_settled(server):
    return lambda: one(server.path, "SELECT COUNT(*) FROM messages WHERE status = 'pending'") == 0


def test_50_clients_one_spot_exactly_one_wins(live):
    state = {}

    def seed(conn):
        state["tokens"], state["cid"] = seed_students(conn, 50, class_capacity=1)

    server = live(seed)
    cid = state["cid"]
    out = hammer(server, state["tokens"], [lambda c: c.post_form(f"/classes/{cid}/book")] * 50)
    statuses = sorted(s for s, _, _ in out)
    assert statuses.count(303) == 1 and statuses.count(409) == 49, statuses
    winner = next(r for s, _, r in out if s == 303)
    assert winner.headers["location"] == "/my-bookings"
    for s, _, r in out:
        if s == 409:
            assert "Class is full" in r.text
    assert one(server.path, "SELECT COUNT(*) FROM bookings WHERE class_id=? AND status='booked'", cid) == 1
    assert one(server.path, "SELECT COUNT(*) FROM bookings") == 1
    # the one booking got exactly one email, the 49 refusals none
    assert server.wait_for(mails_settled(server))
    assert rows(server.path, "SELECT kind, status FROM messages") == [("booked", "recorded")]
    # the schedule agrees: Full, no book action for the class
    page = server.client().get("/").text
    assert "<strong>Full</strong>" in page and "View and book" not in page
    no_server_errors(server)


def test_30_clients_ten_spots_exactly_ten_win_and_p95_is_inside_the_one_second_budget(live):
    state = {}

    def seed(conn):
        state["tokens"], state["cid"] = seed_students(conn, 30, class_capacity=10)

    server = live(seed)
    cid = state["cid"]
    out = hammer(server, state["tokens"], [lambda c: c.post_form(f"/classes/{cid}/book")] * 30)
    statuses = [s for s, _, _ in out]
    assert statuses.count(303) == 10 and statuses.count(409) == 20, sorted(statuses)
    assert one(server.path, "SELECT COUNT(*) FROM bookings WHERE status='booked'") == 10
    assert server.wait_for(mails_settled(server))
    assert one(server.path, "SELECT COUNT(*) FROM messages WHERE kind='booked' AND status='recorded'") == 10
    times = sorted(t for _, t, _ in out)
    p95 = times[int(len(times) * 0.95) - 1]
    print(f"\n[T7] 30 simultaneous bookings: median {statistics.median(times):.3f}s p95 {p95:.3f}s max {times[-1]:.3f}s")
    assert times[-1] < 5.0, "a request waited as long as the lock timeout (would be a 503)"
    assert p95 < 1.0, f"spec NFR: schedule and booking respond in under 1 s (p95); measured {p95:.3f}s"
    no_server_errors(server)


def test_double_click_12_parallel_submits_by_one_student_make_one_booking_and_one_email(live):
    state = {}

    def seed(conn):
        state["tokens"], state["cid"] = seed_students(conn, 1, class_capacity=5)

    server = live(seed)
    cid = state["cid"]
    out = hammer(server, state["tokens"] * 12, [lambda c: c.post_form(f"/classes/{cid}/book")] * 12)
    assert [s for s, _, _ in out] == [303] * 12  # one 'Booked', eleven 'already booked'; no error page
    assert one(server.path, "SELECT COUNT(*) FROM bookings WHERE status='booked'") == 1
    assert server.wait_for(mails_settled(server))
    assert one(server.path, "SELECT COUNT(*) FROM messages") == 1
    no_server_errors(server)


def test_a_cancel_racing_with_19_bookers_never_overbooks_and_spots_stay_consistent(live):
    state = {}

    def seed(conn):
        state["tokens"], state["cid"] = seed_students(conn, 20, class_capacity=1)
        insert_booking(conn, state["cid"], 1)  # student 0 (id 1) holds the only spot

    server = live(seed)
    cid = state["cid"]
    bk = one(server.path, "SELECT id FROM bookings")
    calls = [lambda c: c.post_form(f"/bookings/{bk}/cancel")] + [lambda c: c.post_form(f"/classes/{cid}/book")] * 19
    out = hammer(server, state["tokens"], calls)
    assert out[0][0] == 303  # the holder's cancel is allowed (class is 3 days away)
    winners = sum(1 for s, _, _ in out[1:] if s == 303)
    assert winners <= 1
    assert all(s in (303, 409) for s, _, _ in out), [s for s, _, _ in out]
    booked = one(server.path, "SELECT COUNT(*) FROM bookings WHERE class_id=? AND status='booked'", cid)
    assert booked == winners <= 1
    assert server.wait_for(mails_settled(server))
    kinds = sorted(k for (k,) in rows(server.path, "SELECT kind FROM messages"))
    assert kinds == sorted(["cancelled"] + ["booked"] * winners)
    no_server_errors(server)


def test_admin_cancelling_the_class_while_students_book_leaves_no_booked_row_and_no_email_for_it(live):
    state = {}

    def seed(conn):
        state["tokens"], state["cid"] = seed_students(conn, 20, class_capacity=20)

    server = live(seed)
    cid = state["cid"]
    admin_session = sign_in(server, ADMIN_EMAIL, ADMIN_PASSWORD).cookies["session"]
    tokens = state["tokens"] + [admin_session]
    calls = [lambda c: c.post_form(f"/classes/{cid}/book")] * 20 + [lambda c: c.post_form(f"/admin/classes/{cid}/cancel")]
    out = hammer(server, tokens, calls)
    assert out[-1][0] == 303
    assert all(s in (303, 409) for s, _, _ in out), [s for s, _, _ in out]
    assert one(server.path, "SELECT status FROM classes WHERE id=?", cid) == "cancelled"
    assert one(server.path, "SELECT COUNT(*) FROM bookings WHERE status='booked'") == 0
    assert one(server.path, "SELECT COUNT(*) FROM bookings WHERE status='cancelled' AND cancelled_by='studio'") == \
        one(server.path, "SELECT COUNT(*) FROM bookings")
    assert server.wait_for(mails_settled(server))
    assert one(server.path, "SELECT COUNT(*) FROM messages WHERE kind='cancelled'") == 0  # studio cancel: no mail
    no_server_errors(server)
