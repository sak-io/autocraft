"""T3 unit tests: scrypt, token hashing, sessions, last sign-in, and the admin bootstrap cases (F25)."""
from datetime import datetime, timedelta, timezone

import pytest

from classbook.auth import service
from classbook.auth.bootstrap import BootstrapError, bootstrap_admin
from classbook.auth.passwords import PREFIX, dummy_hash, hash_password, verify_password
from classbook.config import ConfigError, Settings
from classbook.kernel import db
from classbook.kernel.timeutil import FixedClock
from tests.conftest import GOOD_ENV, add_user

NOW = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)


def test_scrypt_hash_verifies_and_is_salted_and_versioned():
    h1, h2 = hash_password("correct horse battery"), hash_password("correct horse battery")
    assert h1 != h2 and h1.startswith(PREFIX + "$")
    assert verify_password("correct horse battery", h1) and not verify_password("wrong", h1)
    assert "correct" not in h1


@pytest.mark.parametrize("bad", ["", "x", "scrypt1$zz$zz", "bcrypt$aa$bb", "scrypt1$aa$bb$cc"])
def test_malformed_stored_hash_never_verifies(bad):
    assert verify_password("anything", bad) is False


def test_dummy_hash_is_valid_but_matches_nothing_practical():
    assert dummy_hash().startswith(PREFIX) and not verify_password("", dummy_hash())


def test_session_token_is_stored_only_as_sha256(conn):
    uid = add_user(conn)
    token = service.create_session(conn, uid, NOW)
    stored = conn.execute("SELECT token_hash FROM sessions").fetchone()[0]
    assert stored != token and stored == service.token_hash(token) and len(stored) == 64
    assert service.session_user(conn, token, NOW)["id"] == uid


def test_forged_malformed_and_expired_tokens_are_rejected(conn):
    uid = add_user(conn)
    token = service.create_session(conn, uid, NOW)
    for bad in (None, "", "short", "x" * 43, token[:-1] + ("A" if token[-1] != "A" else "B"), token + "'; DROP TABLE users;--"):
        assert service.session_user(conn, bad, NOW) is None
    assert service.session_user(conn, token, NOW + timedelta(days=14) - timedelta(seconds=1)) is not None
    assert service.session_user(conn, token, NOW + timedelta(days=14)) is None  # expiry is exclusive


def test_purge_removes_expired_sessions_and_old_failures_only(conn):
    uid = add_user(conn)
    old, live = service.create_session(conn, uid, NOW - timedelta(days=15)), service.create_session(conn, uid, NOW)
    service.record(conn, ["ip:old"], NOW - timedelta(days=2))
    service.record(conn, ["ip:new"], NOW - timedelta(hours=1))
    service.purge_expired(conn, NOW)
    assert service.session_user(conn, live, NOW) and conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 1
    assert [r[0] for r in conn.execute("SELECT key FROM login_failures")] == ["ip:new"]


def test_login_throttle_caps_and_window(conn):
    service.record(conn, [service.email_key("A@x.com")] * 9, NOW)
    assert not service.login_throttled(conn, "a@x.com", "1.1.1.1", NOW)
    service.record(conn, [service.email_key("a@x.com")], NOW)
    assert service.login_throttled(conn, " A@X.com ", "2.2.2.2", NOW)  # per email, any IP, normalised
    assert not service.login_throttled(conn, "a@x.com", "2.2.2.2", NOW + timedelta(minutes=15))  # window passed
    service.record(conn, [service.ip_key("3.3.3.3")] * 19, NOW)
    assert not service.login_throttled(conn, "b@x.com", "3.3.3.3", NOW)
    service.record(conn, [service.ip_key("3.3.3.3")], NOW)
    assert service.login_throttled(conn, "b@x.com", "3.3.3.3", NOW)


def test_last_sign_in_reports_previous_login_and_failures_since(conn):
    uid = add_user(conn, "m@example.com", "admin")
    assert service.last_sign_in(conn, uid) == {"previous": None, "failures_since": 0}
    service.mark_sign_in(conn, uid, NOW)
    service.mark_sign_in(conn, uid, NOW + timedelta(hours=1))
    service.record(conn, [service.email_key("m@example.com")], NOW + timedelta(minutes=5))
    service.record(conn, [service.email_key("m@example.com")], NOW + timedelta(hours=2))
    info = service.last_sign_in(conn, uid)
    assert info["previous"] == "2026-10-10T12:00:00Z" and info["failures_since"] == 2


# ---- admin bootstrap (architecture s5 a-c, F25) ----

def settings_for(tmp_path, **over):
    return Settings.from_env({**GOOD_ENV, "DATABASE_PATH": str(tmp_path / "t.db"), **over})


def rows(path, sql, *args):
    with db.read_conn(path) as c:
        return c.execute(sql, args).fetchall()


@pytest.fixture
def boot(tmp_path):
    db.migrate(tmp_path / "t.db")
    clock = FixedClock(NOW)
    return lambda **over: bootstrap_admin(settings_for(tmp_path, **over), clock), str(tmp_path / "t.db")


def test_bootstrap_a_creates_admin_with_scrypt_hash_and_is_then_idempotent(boot):
    run, path = boot
    assert run() == ["created"]
    (admin,) = rows(path, "SELECT * FROM users")
    assert admin["role"] == "admin" and admin["email"] == "maya@example.com"
    assert verify_password(GOOD_ENV["ADMIN_PASSWORD"], admin["password_hash"]) and GOOD_ENV["ADMIN_PASSWORD"] not in admin["password_hash"]
    assert run() == []


def test_bootstrap_a_refuses_to_promote_an_existing_student_unless_flag(boot):
    run, path = boot
    with db.write_tx(path) as c:
        add_user(c, "maya@example.com", "student")
    with pytest.raises(BootstrapError, match="ADMIN_PROMOTE_EXISTING"):
        run()
    assert rows(path, "SELECT role FROM users")[0]["role"] == "student"
    assert run(ADMIN_PROMOTE_EXISTING="true") == ["promoted"]
    (u,) = rows(path, "SELECT * FROM users")
    assert u["role"] == "admin" and verify_password(GOOD_ENV["ADMIN_PASSWORD"], u["password_hash"])  # env password now rules


def test_bootstrap_b_refuses_email_change_unless_flag_and_ends_old_sessions(boot):
    run, path = boot
    run()
    with db.write_tx(path) as c:
        service.create_session(c, rows(path, "SELECT id FROM users")[0]["id"], NOW)
    with pytest.raises(BootstrapError, match="ADMIN_ALLOW_EMAIL_CHANGE"):
        run(ADMIN_EMAIL="new@example.com")
    assert rows(path, "SELECT email FROM users")[0]["email"] == "maya@example.com"
    assert run(ADMIN_EMAIL="new@example.com", ADMIN_ALLOW_EMAIL_CHANGE="true") == ["email_changed"]
    assert rows(path, "SELECT email FROM users")[0]["email"] == "new@example.com"
    assert rows(path, "SELECT COUNT(*) AS n FROM sessions")[0]["n"] == 0


def test_bootstrap_b_refuses_even_with_flag_if_new_email_belongs_to_a_student(boot):
    run, path = boot
    run()
    with db.write_tx(path) as c:
        add_user(c, "new@example.com", "student")
    with pytest.raises(BootstrapError, match="already used"):
        run(ADMIN_EMAIL="new@example.com", ADMIN_ALLOW_EMAIL_CHANGE="true")


def test_bootstrap_c_env_password_change_resets_stored_password(boot):
    run, path = boot
    run()
    assert run(ADMIN_PASSWORD="a-brand-new-password-99") == ["password_reset"]
    (u,) = rows(path, "SELECT password_hash FROM users")
    assert verify_password("a-brand-new-password-99", u["password_hash"]) and not verify_password(GOOD_ENV["ADMIN_PASSWORD"], u["password_hash"])


def test_admin_password_shorter_than_14_refuses_to_start(tmp_path):
    with pytest.raises(ConfigError) as e:
        settings_for(tmp_path, ADMIN_PASSWORD="only-13-chars")
    assert "ADMIN_PASSWORD" in str(e.value) and "only-13-chars" not in str(e.value)
    settings_for(tmp_path, ADMIN_PASSWORD="exactly-14-chr!")  # 14 is fine


def test_bootstrap_failure_messages_do_not_contain_the_password_or_email(boot):
    run, path = boot
    with db.write_tx(path) as c:
        add_user(c, "maya@example.com", "student")
    with pytest.raises(BootstrapError) as e:
        run()
    assert GOOD_ENV["ADMIN_PASSWORD"] not in str(e.value) and "maya@example.com" not in str(e.value)
