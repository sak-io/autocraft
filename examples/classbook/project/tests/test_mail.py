"""T6: confirmation emails. Own fixtures (no shared admin/student ids with tests/test_bookings.py)."""
import io
import logging
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

import classbook.mail as mail
from classbook.app import create_app
from classbook.config import ConfigError, Settings
from classbook.kernel import db
from classbook.kernel.timeutil import FixedClock, to_text
from classbook.logging_setup import JsonFormatter, logger
from classbook.mail import RecordingMailer, build_mailer
from classbook.mail.outbox import send_confirmation
from classbook.mail.templates import UnsafeMessage, render
from classbook.web.deps import User, current_user
from tests.conftest import add_booking, add_class, add_user

NOW = datetime(2026, 10, 10, 12, 0, 0, tzinfo=timezone.utc)  # BST (UTC+1) in London
T = lambda **d: to_text(NOW + timedelta(**d))  # noqa: E731
TOK = "t" * 43


# ---------- unit: templates ----------

def test_booked_message_has_title_london_time_and_word_booked():
    subject, body = render("booked", "s@example.com", "Vinyasa Flow", NOW + timedelta(days=3))
    assert "Vinyasa Flow" in subject and "booked" in subject
    assert "Vinyasa Flow" in body and "Tue 13 Oct 2026, 13:00 (London time)" in body and "booked" in body and "cancelled" not in body


def test_cancelled_message_says_cancelled_and_winter_time_is_gmt():
    start = datetime(2026, 12, 1, 18, 30, tzinfo=timezone.utc)
    subject, body = render("cancelled", "s@example.com", "Yin", start)
    assert "cancelled" in subject and "Tue 01 Dec 2026, 18:30" in body and "booked" not in body


@pytest.mark.parametrize("title", ["Yoga <b>&amp;</b> \"quotes\" 'x'", "100% {0} {name} %s $HOME", "Café ☯ 瑜伽 😀", "x" * 100, "Evil‮RTL"])
def test_odd_titles_are_kept_verbatim_in_plain_text(title):
    subject, body = render("booked", "s@example.com", title, NOW)
    assert title in subject and f"Class: {title}\n" in body and "\n" not in subject


@pytest.mark.parametrize("bad", ["Flow\nBcc: x@evil.com", "Flow\r\nX: y", "a\x00b", "tab\there", "bell\x07", "next\x85line", "ls x"])
def test_control_characters_in_title_or_address_are_rejected(bad):
    with pytest.raises(UnsafeMessage):
        render("booked", "s@example.com", bad, NOW)
    with pytest.raises(UnsafeMessage):
        render("booked", f"s@example.com{bad}", "Flow", NOW)


def test_empty_title_and_unknown_kind_are_rejected():
    with pytest.raises(UnsafeMessage):
        render("booked", "s@example.com", "  ", NOW)
    with pytest.raises(ValueError):
        render("reminder", "s@example.com", "Flow", NOW)


def test_error_text_never_contains_the_data():
    with pytest.raises(UnsafeMessage) as e:
        render("booked", "secret@example.com", "Evil\nTitle", NOW)
    assert "secret" not in str(e.value) and "Evil" not in str(e.value)


# ---------- unit: mailer and config ----------

def test_recording_mailer_accepts_normal_and_rejects_header_injection():
    m = RecordingMailer()
    m.send("s@example.com", "Class booked: Flow", "body")
    for to, subj in (("s@example.com\nBcc: x@y.z", "s"), ("s@example.com", "s\r\nBcc: x@y.z"), ("no-at-sign", "s")):
        with pytest.raises(ValueError):
            m.send(to, subj, "b")


def test_factory_default_is_the_recording_mailer_not_the_null_mailer(env):
    """N-4 (T2 review): fails if the app factory still wires NullMailer (or anything that drops mail)."""
    app = create_app(Settings.from_env(env), FixedClock(NOW))
    assert isinstance(app.state.mailer, RecordingMailer)
    assert type(app.state.mailer).__name__ != "NullMailer" and not hasattr(mail, "NullMailer")
    assert isinstance(build_mailer(Settings.from_env(env)), RecordingMailer)


@pytest.mark.parametrize("backend", ["smtp", "sendgrid", "RECORDING ", "null", "console"])
def test_other_mail_backends_refuse_start_with_a_clear_message(env, backend):
    with pytest.raises(ConfigError) as e:
        Settings.from_env({**env, "MAIL_BACKEND": backend})
    assert "MAIL_BACKEND" in str(e.value) and "recording" in str(e.value)
    with pytest.raises(SystemExit):  # the real start path
        import os
        old = dict(os.environ)
        os.environ.update({**env, "MAIL_BACKEND": backend})
        try:
            create_app()
        finally:
            os.environ.clear(); os.environ.update(old)


# ---------- integration ----------

class Spy:
    """Mailer stub: records calls; optionally fails; checks that no write lock or open transaction exists when called."""
    def __init__(self, path, fail=False):
        self.path, self.fail, self.calls, self.lock_free, self.saw_booking = path, fail, [], [], []

    def send(self, to, subject, body):
        c = sqlite3.connect(self.path, timeout=0, isolation_level=None)
        try:
            c.execute("BEGIN IMMEDIATE"); c.execute("ROLLBACK"); self.lock_free.append(True)
            self.saw_booking.append(c.execute("SELECT COUNT(*) FROM bookings").fetchone()[0])
        except sqlite3.OperationalError:
            self.lock_free.append(False)
        finally:
            c.close()
        self.calls.append((to, subject, body))
        if self.fail:
            raise RuntimeError("smtp down for secret-user@example.com")


@pytest.fixture
def site(env):
    """App with its own users: admin id 1 (bootstrap), students 2 (s1) and 3 (s2); class 1 is 3 days out, capacity 2."""
    clock = FixedClock(NOW)
    app = create_app(Settings.from_env(env), clock)
    c = db.connect(env["DATABASE_PATH"])
    add_user(c, "s1@example.com"); add_user(c, "s2@example.com"); add_class(c, T(days=3), 2)
    c.close()
    who = {"user": User(2, "s1@example.com", "S1", "student")}
    app.dependency_overrides[current_user] = lambda: who["user"]
    app.state.mailer = Spy(env["DATABASE_PATH"])
    client = TestClient(app, follow_redirects=False)
    client.cookies.set("csrf", TOK)
    client.who, client.path, client.clock, client.spy = who, env["DATABASE_PATH"], clock, app.state.mailer
    return client


def post(c, url):
    return c.post(url, data={"csrf_token": TOK})


def q(c, sql, *a):
    conn = db.connect(c.path)
    try:
        return [tuple(r) for r in conn.execute(sql, a).fetchall()]
    finally:
        conn.close()


def msgs(c):
    return q(c, "SELECT to_email, subject, body, kind, booking_id, status FROM messages ORDER BY id")


@pytest.fixture
def logs():
    buf = io.StringIO()
    h = logging.StreamHandler(buf)
    h.setFormatter(JsonFormatter())
    logger.addHandler(h)
    yield buf
    logger.removeHandler(h)


def test_booking_sends_exactly_one_recorded_message_after_commit(site):
    r = post(site, "/classes/1/book")
    assert r.status_code == 303
    [(to, subject, body, kind, bid, status)] = msgs(site)
    assert (to, kind, status, bid) == ("s1@example.com", "booked", "recorded", 1)
    assert "Flow" in subject and "Tue 13 Oct 2026, 13:00" in body and "booked" in body
    assert site.spy.calls == [(to, subject, body)]
    assert site.spy.lock_free == [True] and site.spy.saw_booking == [1]  # committed, and no transaction open while sending


def test_cancelling_sends_one_cancellation_message(site):
    post(site, "/classes/1/book")
    r = post(site, "/bookings/1/cancel")
    assert r.status_code == 303
    rows = msgs(site)
    assert [(m[3], m[4], m[5]) for m in rows] == [("booked", 1, "recorded"), ("cancelled", 1, "recorded")]
    assert "cancelled" in rows[1][1] and "Flow" in rows[1][2]


def test_failing_mailer_leaves_booking_intact_count_correct_error_logged_row_failed(site, logs):
    site.spy.fail = True
    r = post(site, "/classes/1/book")
    assert r.status_code == 303 and r.headers["location"] == "/my-bookings"
    assert q(site, "SELECT status FROM bookings") == [("booked",)]
    assert "Flow" in site.get("/my-bookings").text
    [(_, _, _, kind, _, status)] = msgs(site)
    assert (kind, status) == ("booked", "failed")
    out = logs.getvalue()
    assert "message send failed" in out and "RuntimeError" in out
    assert "secret-user" not in out and "s1@example.com" not in out and "Flow" not in out  # no user data in logs
    r2 = post(site, "/bookings/1/cancel")  # cancelling with a failing mailer works too
    assert r2.status_code == 303 and q(site, "SELECT status FROM bookings") == [("cancelled",)]
    assert [m[5] for m in msgs(site)] == ["failed", "failed"]


def test_mail_failure_does_not_change_the_http_result(site):
    ok = post(site, "/classes/1/book")
    site.who["user"] = User(3, "s2@example.com", "S2", "student")
    site.spy.fail = True
    bad = post(site, "/classes/1/book")
    assert (ok.status_code, ok.headers["location"]) == (bad.status_code, bad.headers["location"])
    assert q(site, "SELECT COUNT(*) FROM bookings WHERE status='booked'") == [(2,)]
    assert len(site.spy.calls) == 2  # both attempts were mailed (and the failing one did not stop the first)


def test_spots_left_stays_correct_when_mail_fails(site, env):
    site.spy.fail = True
    post(site, "/classes/1/book")
    c = db.connect(env["DATABASE_PATH"])
    try:
        from classbook.kernel import rules
        assert rules.spots_left(c, 1) == 1
    finally:
        c.close()


def test_duplicate_request_sends_one_email(site):
    a, b = post(site, "/classes/1/book"), post(site, "/classes/1/book")
    assert a.status_code == b.status_code == 303
    assert len(msgs(site)) == 1 and len(site.spy.calls) == 1
    post(site, "/bookings/1/cancel"); post(site, "/bookings/1/cancel")
    assert [m[3] for m in msgs(site)] == ["booked", "cancelled"] and len(site.spy.calls) == 2


def test_unique_guard_blocks_a_second_message_even_if_called_twice(env):
    clock, path = FixedClock(NOW), env["DATABASE_PATH"]
    create_app(Settings.from_env(env), clock)
    c = db.connect(path); u = add_user(c); k = add_class(c, T(days=3)); b = add_booking(c, k, u); c.close()
    spy = Spy(path)
    for _ in range(3):
        send_confirmation(path, clock, spy, kind="booked", booking_id=b, to_email="s@example.com", class_title="Flow", starts_at=NOW)
    assert len(spy.calls) == 1
    conn = db.connect(path)
    assert conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 1
    conn.close()


def test_rebooking_after_cancel_is_a_new_booking_with_its_own_message(site):
    for url in ("/classes/1/book", "/bookings/1/cancel", "/classes/1/book"):
        post(site, url)
    assert [(m[3], m[4]) for m in msgs(site)] == [("booked", 1), ("cancelled", 1), ("booked", 2)]


def test_refusals_noops_and_missing_things_send_nothing(site):
    c = db.connect(site.path)
    full = add_class(c, T(days=3), 1); add_booking(c, full, 3)               # id 2: full
    started = add_class(c, T(hours=-1), 5)                                    # id 3: started
    far = add_class(c, T(days=40), 5)                                         # id 4: not open yet
    cancelled = add_class(c, T(days=3), 5, "cancelled")                       # id 5: studio cancelled
    soon = add_class(c, T(hours=5), 5); soon_b = add_booking(c, soon, 2)      # id 6: booking within 12h
    studio = add_booking(c, 1, 2, "cancelled")                                # a cancelled booking, marked as studio-cancelled below
    c.execute("UPDATE bookings SET cancelled_by='studio' WHERE id=?", (studio,)); c.commit(); c.close()
    for cid, expect in ((full, 409), (started, 409), (far, 409), (cancelled, 409), (999, 404)):
        assert post(site, f"/classes/{cid}/book").status_code == expect
    assert post(site, f"/bookings/{soon_b}/cancel").status_code == 409          # too late
    assert post(site, f"/bookings/{studio}/cancel").status_code == 303          # already cancelled: no-op
    assert post(site, "/bookings/999/cancel").status_code == 404
    site.who["user"] = User(1, "maya@example.com", "Maya", "admin")
    assert post(site, "/classes/1/book").status_code == 403
    site.who["user"] = None
    assert post(site, "/classes/1/book").status_code == 303                      # anonymous -> login
    assert msgs(site) == [] and site.spy.calls == []


def test_csrf_failure_sends_nothing(site):
    assert site.post("/classes/1/book", data={"csrf_token": "wrong"}).status_code == 403
    assert msgs(site) == []


def test_studio_cancelling_a_class_sends_no_email(site):
    """The admin route is T4's; the studio-cancel effect is simulated in SQL. Nothing in the app mails on it."""
    post(site, "/classes/1/book")
    c = db.connect(site.path)
    c.execute("UPDATE classes SET status='cancelled' WHERE id=1")
    c.execute("UPDATE bookings SET status='cancelled', cancelled_by='studio' WHERE id=1"); c.commit(); c.close()
    assert len(msgs(site)) == 1 and len(site.spy.calls) == 1  # only the original booking mail


def test_hourly_cap_also_caps_mail(site):
    for i in range(10):
        post(site, "/classes/1/book"); post(site, f"/bookings/{i + 1}/cancel")
    assert len(msgs(site)) == 20
    assert post(site, "/classes/1/book").status_code == 429
    assert len(msgs(site)) == 20 and len(site.spy.calls) == 20


def test_unsafe_class_title_blocks_the_mail_but_not_the_booking(site, logs):
    c = db.connect(site.path); c.execute("UPDATE classes SET title='Flow' || char(10) || 'Bcc: x@evil.com' WHERE id=1"); c.commit(); c.close()
    assert post(site, "/classes/1/book").status_code == 303
    assert q(site, "SELECT status FROM bookings") == [("booked",)] and msgs(site) == [] and site.spy.calls == []
    assert "message not queued" in logs.getvalue() and "evil" not in logs.getvalue()


def test_a_failing_status_update_is_logged_and_leaves_the_booking_alone(site, logs, monkeypatch):
    real = db.write_tx
    n = {"i": 0}

    def flaky(path, *a, **k):
        n["i"] += 1
        if n["i"] == 3:  # 1 = booking tx, 2 = pending row, 3 = status update
            raise db.DatabaseBusy()
        return real(path, *a, **k)
    monkeypatch.setattr(db, "write_tx", flaky)
    assert post(site, "/classes/1/book").status_code == 303
    assert q(site, "SELECT status FROM bookings") == [("booked",)] and msgs(site)[0][5] == "pending"
    assert "message status not saved" in logs.getvalue()
