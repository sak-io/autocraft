"""T7 (6): the follow-ups the per-task reviews handed to T7. Each test is written so that a specific
"mutant" (a plausible wrong change to production code) fails it; the QA summary lists the mutants tried.
"""
import asyncio
import hashlib
import re
import threading
from contextlib import contextmanager

import pytest

from classbook.app import create_app
from classbook.auth import passwords
from classbook.auth.passwords import hash_password
from classbook.config import Settings
from classbook.kernel import db
from classbook.kernel.timeutil import FixedClock
from tests.qa.support import (ADMIN_EMAIL, ADMIN_PASSWORD, NOW, PASSWORD, TOKEN, AppBrowser, csrf_in, env_for,
                              insert_user, one, rows, session_for)
from tests.qa.test_authz_matrix import fingerprint


# ---------------------------------------------------------------------------------------------------------
# T6 M-1: the confirmation email is sent AFTER the response, not inline in the request
# ---------------------------------------------------------------------------------------------------------
def drive_asgi(app, method, path, form: dict, cookies: dict):
    """Call the ASGI app directly and return the ordered list of 'what happened' (response parts, mailer calls)."""
    from urllib.parse import urlencode
    body = urlencode(form).encode()
    cookie = "; ".join(f"{k}={v}" for k, v in cookies.items())
    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": method, "path": path,
             "raw_path": path.encode(), "query_string": b"", "root_path": "", "scheme": "http",
             "server": ("testserver", 80), "client": ("127.0.0.1", 5000),
             "headers": [(b"host", b"testserver"), (b"cookie", cookie.encode()),
                         (b"content-type", b"application/x-www-form-urlencoded"),
                         (b"content-length", str(len(body)).encode())]}
    events: list[str] = []
    sent = {"done": False}

    async def receive():
        if not sent["done"]:
            sent["done"] = True
            return {"type": "http.request", "body": body, "more_body": False}
        await asyncio.sleep(3600)  # a real client stays connected until the response is complete

    async def send(message):
        if message["type"] == "http.response.start":
            events.append("response.start")
        elif message["type"] == "http.response.body" and not message.get("more_body"):
            events.append("response.complete")

    class Spy:
        def send(self, to, subject, body):
            events.append("mailer.send")

    app.state.mailer = Spy()
    asyncio.run(asyncio.wait_for(app(scope, receive, send), 30))
    return events


def test_confirmation_mail_is_sent_after_the_response_is_complete_not_inline(world):
    token = session_for(world.path, world.ids["b"])
    events = drive_asgi(world.app, "POST", f"/classes/{world.ids['c1']}/book",
                        {"csrf_token": TOKEN}, {"session": token, "csrf": TOKEN})
    assert events == ["response.start", "response.complete", "mailer.send"], events


def test_cancellation_mail_is_also_sent_after_the_response(world):
    token = session_for(world.path, world.ids["a"])
    events = drive_asgi(world.app, "POST", f"/bookings/{world.ids['booking_a']}/cancel",
                        {"csrf_token": TOKEN}, {"session": token, "csrf": TOKEN})
    assert events == ["response.start", "response.complete", "mailer.send"], events


# ---------------------------------------------------------------------------------------------------------
# T6 M-2 / threat T-17: nothing the student chose (name, email) is echoed into the message
# ---------------------------------------------------------------------------------------------------------
def test_message_subject_and_body_contain_the_facts_but_not_the_students_name_or_email(world):
    with db.write_tx(world.path) as conn:
        uid = insert_user(conn, "quokka.unique@example.com", "Zed <b>Quokka</b> ‮")
    browser = world.browser(None)
    browser.cookies.set("session", session_for(world.path, uid))
    assert browser.post_form(f"/classes/{world.ids['c1']}/book").status_code == 303
    (to, subject, body, kind), = rows(world.path, "SELECT to_email, subject, body, kind FROM messages")
    assert to == "quokka.unique@example.com" and kind == "booked"
    text = (subject + "\n" + body).lower()
    for private in ("quokka", "zed", "unique", "@", "<b>"):
        assert private not in text, f"{private!r} leaked into the message"
    assert "flow" in text and "booked" in text and "(london time)" in text  # AC-4b.1 facts
    assert re.search(r"\b\d{2} oct 2026, \d{2}:\d{2}\b", body.lower().replace("(london time)", ""))  # 13 Oct 2026, 12:00


def test_cancellation_message_has_title_time_and_the_word_cancelled(world):
    assert world.browser("a").post_form(f"/bookings/{world.ids['booking_a']}/cancel").status_code == 303
    (subject, body, kind), = rows(world.path, "SELECT subject, body, kind FROM messages")
    assert kind == "cancelled"
    for text in (subject, body):
        assert "Flow" in text and "cancelled" in text and "13 Oct 2026, 13:00" in text  # 12:00Z is 13:00 BST
    assert "Alice" not in body and "a@example.com" not in body


# ---------------------------------------------------------------------------------------------------------
# T3 minors / ADR-0003 conditions
# ---------------------------------------------------------------------------------------------------------
def test_scrypt_parameters_and_hash_format_are_pinned_to_the_adr(tmp_path):
    assert (passwords.N, passwords.R, passwords.P, passwords.DKLEN) == (2**14, 8, 1, 32)
    stored = hash_password("some password")
    assert re.fullmatch(r"scrypt1\$[0-9a-f]{32}\$[0-9a-f]{64}", stored)
    assert stored != hash_password("some password")  # per-user random salt
    _, salt, digest = stored.split("$")
    independent = hashlib.scrypt(b"some password", salt=bytes.fromhex(salt), n=2**14, r=8, p=1, dklen=32,
                                 maxmem=64 * 1024 * 1024)
    assert independent.hex() == digest, "stored hash is not plain scrypt N=2^14 r=8 p=1 over the UTF-8 password"


@pytest.fixture
def no_hashing_in_tx(monkeypatch):
    """Records every scrypt call and fails it if a write transaction is open on this thread."""
    state = threading.local()
    real_tx, real_kdf = db.write_tx, passwords._kdf
    calls: list[str] = []

    @contextmanager
    def tracked(*args, **kw):
        with real_tx(*args, **kw) as conn:
            state.depth = getattr(state, "depth", 0) + 1
            try:
                yield conn
            finally:
                state.depth -= 1

    def kdf(password, salt):
        calls.append("scrypt")
        assert getattr(state, "depth", 0) == 0, "scrypt ran inside a write transaction (blocks every other writer)"
        return real_kdf(password, salt)

    monkeypatch.setattr(db, "write_tx", tracked)
    monkeypatch.setattr(passwords, "_kdf", kdf)
    return calls


def test_no_password_hashing_inside_a_write_transaction_signup_login_and_bootstrap(tmp_path, no_hashing_in_tx):
    calls = no_hashing_in_tx
    path = tmp_path / "h.db"
    app = create_app(Settings.from_env(env_for(path)), FixedClock(NOW))      # bootstrap case a: hash
    n_boot = len(calls)
    assert n_boot >= 1
    # restart with the same env (case: verify) and with a NEW env password (case c: verify fails, reset: hash)
    create_app(Settings.from_env(env_for(path)), FixedClock(NOW))
    create_app(Settings.from_env({**env_for(path), "ADMIN_PASSWORD": "a-different-admin-password-9"}), FixedClock(NOW))
    assert len(calls) >= n_boot + 3
    passwords.dummy_hash()  # warmed by hand here: see the D-4 test below for the lazily built default
    before = len(calls)
    b = AppBrowser(app)
    page = b.get("/signup")
    r = b.post("/signup", data={"csrf_token": csrf_in(page.text), "name": "N", "email": "n@example.com", "password": PASSWORD})
    assert r.status_code == 303
    assert len(calls) == before + 1  # signup hashes once
    for email, password, status in (("n@example.com", PASSWORD, 303), ("n@example.com", "wrong-password-1", 401),
                                    ("ghost@example.com", "whatever-123456", 401)):
        c = AppBrowser(app)
        page = c.get("/login")
        n = len(calls)
        assert c.post("/login", data={"csrf_token": csrf_in(page.text), "email": email, "password": password}).status_code == status
        assert len(calls) == n + 1, "login (success, wrong password, unknown email) must pay exactly one scrypt"


def test_overlong_passwords_never_crash_login_or_signup(world):
    with db.write_tx(world.path) as conn:
        insert_user(conn, "pw@example.com", "Pw", password="x" * 128)
    for pw in ("y" * 129, "y" * 5000, "é" * 129, "\U0001f600" * 300):
        b = AppBrowser(world.app)
        page = b.get("/login")
        r = b.post("/login", data={"csrf_token": csrf_in(page.text), "email": "pw@example.com", "password": pw})
        assert r.status_code == 401, (len(pw), r.status_code)
        page = b.get("/signup")
        r = b.post("/signup", data={"csrf_token": csrf_in(page.text), "name": "N", "email": "n2@example.com", "password": pw})
        assert r.status_code == 422 and "128" in r.text, (len(pw), r.status_code)
    b = AppBrowser(world.app)
    page = b.get("/login")
    ok = b.post("/login", data={"csrf_token": csrf_in(page.text), "email": "pw@example.com", "password": "x" * 128})
    assert ok.status_code == 303  # exactly 128 characters is a valid password


def test_dummy_hash_is_warmed_at_startup(tmp_path):
    passwords.dummy_hash.cache_clear()
    create_app(Settings.from_env(env_for(tmp_path / "d.db")), FixedClock(NOW))
    assert passwords.dummy_hash.cache_info().currsize == 1, "first unknown-email login will pay two scrypts"


# ---------------------------------------------------------------------------------------------------------
# T5 M-3: lock timeout answers 503 on every write route, and nothing is written
# ---------------------------------------------------------------------------------------------------------
@pytest.fixture
def short_lock_timeout(monkeypatch):
    real = db.write_tx
    monkeypatch.setattr(db, "write_tx", lambda path, ms=50: real(path, ms))


def test_every_write_route_answers_503_when_the_database_is_locked_and_writes_nothing(world, short_lock_timeout):
    ids = world.ids
    with db.write_tx(world.path) as conn:  # real, hashable password for the login case
        insert_user(conn, "login@example.com", "Login Person", password=PASSWORD)
    cases = {
        "book": ("b", "POST", f"/classes/{ids['c1']}/book", {}),
        "cancel": ("a", "POST", f"/bookings/{ids['booking_a']}/cancel", {}),
        "admin create": ("admin", "POST", "/admin/classes", {"title": "T", "starts_at": "2026-11-20T10:00",
                                                              "duration_min": "60", "instructor": "I", "capacity": "5"}),
        "admin update": ("admin", "POST", f"/admin/classes/{ids['c1']}", {"title": "T", "starts_at": "2026-11-20T10:00",
                                                                          "duration_min": "60", "instructor": "I", "capacity": "5"}),
        "admin cancel": ("admin", "POST", f"/admin/classes/{ids['c1']}/cancel", {}),
        "signup": (None, "POST", "/signup", {"name": "New", "email": "new@example.com", "password": PASSWORD}),
        "login": (None, "POST", "/login", {"email": "login@example.com", "password": PASSWORD}),
        "logout": ("a", "POST", "/logout", {}),
    }
    browsers = {name: world.browser(who) for name, (who, *_rest) in cases.items()}  # sessions need the lock: make them first
    reader = world.browser(None)
    before = fingerprint(world.path)
    extra_before = (one(world.path, "SELECT COUNT(*) FROM user_actions"), one(world.path, "SELECT COUNT(*) FROM login_failures"))
    holder = db.connect(world.path)
    holder.execute("BEGIN IMMEDIATE")
    try:
        for name, (_who, method, path, data) in cases.items():
            resp = browsers[name].post_form(path, data)
            assert resp.status_code == 503, f"{name}: {resp.status_code}"
            assert resp.headers["retry-after"] == "5" and "busy" in resp.text.lower(), name
        # read-only pages keep working while a writer holds the lock (WAL)
        assert [reader.get(p).status_code for p in ("/", f"/classes/{ids['c1']}", "/health", "/login")] == [200] * 4
    finally:
        holder.execute("ROLLBACK")
        holder.close()
    assert fingerprint(world.path) == before, "a 503 request changed data"
    assert (one(world.path, "SELECT COUNT(*) FROM user_actions"), one(world.path, "SELECT COUNT(*) FROM login_failures")) == extra_before
    # and the app recovers by itself once the lock is gone
    assert world.browser("b").post_form(f"/classes/{ids['c1']}/book").status_code == 303
    assert one(world.path, "SELECT COUNT(*) FROM bookings WHERE status='booked'") == 2


# ---------------------------------------------------------------------------------------------------------
# T6 N-4: the REAL T4 class-cancel route sends no email (AC-6.3, spec Q5)
# ---------------------------------------------------------------------------------------------------------
def test_studio_cancelling_a_class_sends_no_mail_on_the_real_route_even_twice(world):
    c1 = world.ids["c1"]
    assert world.browser("b").post_form(f"/classes/{c1}/book").status_code == 303   # one real booking mail
    assert rows(world.path, "SELECT kind FROM messages") == [("booked",)]
    admin = world.browser("admin")
    assert admin.post_form(f"/admin/classes/{c1}/cancel").status_code == 303
    assert admin.post_form(f"/admin/classes/{c1}/cancel").status_code == 303        # second click: no-op
    assert rows(world.path, "SELECT kind FROM messages") == [("booked",)]
    # both students' bookings are 'cancelled by the studio' and shown that way (AC-4.1 / 6.3)
    assert "Cancelled by the studio" in world.browser("a").get("/my-bookings").text
    assert "Cancelled by the studio" in world.browser("b").get("/my-bookings").text
    # nothing left in the pipeline
    assert one(world.path, "SELECT COUNT(*) FROM messages WHERE status = 'pending'") == 0
