"""H1 regression tests for the 2026-10-10 audit: M-2, L-3, L-5, L-7."""
import os
import stat
from datetime import timedelta

from classbook.app import create_app
from classbook.auth import service
from classbook.config import Settings
from classbook.kernel import db
from classbook.kernel.timeutil import FixedClock, to_text
from classbook.web.middleware import CSP, HSTS
from tests.qa.support import NOW, env_for


def test_m2_throttled_signup_attempts_write_no_rows(tmp_path):
    path = tmp_path / "m2.db"
    db.migrate(path)
    with db.write_tx(path) as conn:
        for _ in range(service.SIGNUP_CAP):
            service.record(conn, [service.signup_key("testclient")], NOW)
        assert service.signup_throttled(conn, "testclient", NOW)
    from fastapi.testclient import TestClient
    app = create_app(Settings.from_env(env_for(path)), FixedClock(NOW))
    c = TestClient(app, raise_server_exceptions=False)
    c.get("/signup")
    for _ in range(3):
        c.post("/signup", data={"csrf_token": c.cookies.get("csrf", ""), "name": "x", "email": "x@e.com", "password": "p" * 12})
    with db.read_conn(path) as conn:
        n = conn.execute("SELECT COUNT(*) FROM login_failures WHERE key LIKE 'signup:%'").fetchone()[0]
    assert n <= service.SIGNUP_CAP


def test_l3_purge_removes_old_user_actions_and_messages(tmp_path):
    path = tmp_path / "l3.db"
    db.migrate(path)
    old, new = NOW - timedelta(days=200), NOW
    with db.write_tx(path) as conn:
        conn.execute("INSERT INTO users (id, email, name, password_hash, role, created_at) VALUES (1,'a@e.com','A','x','student',?)", (to_text(old),))
        for t in (old, new):
            conn.execute("INSERT INTO user_actions (user_id, at) VALUES (1, ?)", (to_text(t),))
            conn.execute("INSERT INTO messages (to_email, subject, body, kind, status, created_at) VALUES ('a@e.com','s','b',?, 'recorded', ?)",
                         (f"k{t.day}{t.year}", to_text(t)))
        service.purge_expired(conn, NOW)
        assert conn.execute("SELECT COUNT(*) FROM user_actions").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 1


def test_l5_security_headers_policy():
    for part in ("form-action 'self'", "base-uri 'none'", "frame-ancestors 'none'", "default-src 'self'"):
        assert part in CSP
    assert "includeSubDomains" in HSTS


def test_l7_database_file_is_owner_only(tmp_path):
    old = os.umask(0o022)
    try:
        path = tmp_path / "l7.db"
        create_app(Settings.from_env(env_for(path)), FixedClock(NOW))
    finally:
        os.umask(old)
    assert stat.S_IMODE(os.stat(path).st_mode) & 0o077 == 0
