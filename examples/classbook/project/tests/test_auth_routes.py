"""T3 integration tests: sign up / log in / log out over HTTP with a real temp-file SQLite (production pragmas)."""
import re
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from classbook.app import create_app
from classbook.config import Settings
from classbook.kernel import db
from classbook.kernel.timeutil import FixedClock
from tests.conftest import GOOD_ENV

NOW = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)
PW = "a-good-student-password"


class Site:
    def __init__(self, env, **over):
        self.settings = Settings.from_env({**env, **over})
        self.clock = FixedClock(NOW)
        self.app = create_app(self.settings, self.clock)
        self.prod = self.settings.is_production
        self.path = self.settings.database_path

    def client(self):
        return TestClient(self.app, base_url="https://testserver" if self.prod else "http://testserver")

    def csrf(self, c, path="/login"):
        c.get(path)
        return c.cookies.get("__Host-csrf" if self.prod else "csrf")

    def post(self, c, path, headers=None, **form):
        form.setdefault("csrf_token", self.csrf(c))
        return c.post(path, data=form, headers=headers or {}, follow_redirects=False)

    def signup(self, c, email="sam@example.com", name="Sam", password=PW, **kw):
        return self.post(c, "/signup", email=email, name=name, password=password, **kw)

    def login(self, c, email="sam@example.com", password=PW, headers=None, **kw):
        return self.post(c, "/login", headers=headers, email=email, password=password, **kw)

    def rows(self, sql, *a):
        with db.read_conn(self.path) as c:
            return c.execute(sql, a).fetchall()

    @property
    def cookie(self):
        return "__Host-session" if self.prod else "session"


@pytest.fixture
def site(env):
    return Site(env)


@pytest.fixture
def client(site):
    return site.client()


def who(client):
    """What the nav shows: anonymous pages link to Sign in; signed-in pages have the Sign out form."""
    return "Sign out" in client.get("/login").text


# ---- sign up (AC-2.1, AC-2.2) ----

def test_signup_creates_student_signs_in_and_redirects(site, client):
    r = site.signup(client)
    assert r.status_code == 303 and r.headers["location"] == "/"
    (u,) = site.rows("SELECT * FROM users WHERE role='student'")
    assert u["role"] == "student" and u["email"] == "sam@example.com" and PW not in u["password_hash"]
    assert who(client)


def test_signup_normalises_email_and_follows_safe_next_only(site, client):
    r = site.signup(client, email="  Sam@Example.COM ", next="/classes/7")
    assert r.headers["location"] == "/classes/7" and site.rows("SELECT email FROM users WHERE role='student'")[0][0] == "sam@example.com"
    r2 = site.signup(site.client(), email="b@example.com", next="//evil.com")
    assert r2.headers["location"] == "/"


@pytest.mark.parametrize("over,field", [({"name": ""}, "name"), ({"email": "nope"}, "email"), ({"password": "short"}, "password"),
                                        ({"password": "x" * 129}, "password"), ({"name": "a\nb"}, "name")])
def test_signup_validation_422_per_field_and_never_echoes_password(site, client, over, field):
    r = site.signup(client, **over)
    assert r.status_code == 422 and site.rows("SELECT * FROM users WHERE role='student'") == []
    assert "flash error" in r.text and "x" * 129 not in r.text and "short" not in r.text.replace("shortly", "")


def test_signup_duplicate_email_is_a_generic_422_and_identical_to_other_failures_in_shape(site, client):
    site.signup(client)
    r = site.signup(site.client())
    assert r.status_code == 422 and "could not create an account with these details" in r.text
    assert "already exists" not in r.text.lower() and "already registered" not in r.text.lower() and len(site.rows("SELECT * FROM users WHERE role='student'")) == 1


def test_signup_requires_csrf(site, client):
    r = client.post("/signup", data={"name": "S", "email": "s@example.com", "password": PW}, follow_redirects=False)
    assert r.status_code == 403 and site.rows("SELECT * FROM users WHERE role='student'") == []


# ---- login (AC-2.3, AC-2.4) ----

def test_login_success_new_session_next_and_last_sign_in(site, client):
    site.signup(site.client())
    r = site.login(client, next="/classes/3")
    assert r.status_code == 303 and r.headers["location"] == "/classes/3"
    cookies = r.headers.get_list("set-cookie")
    sess = next(c for c in cookies if c.startswith("session="))
    assert "HttpOnly" in sess and "SameSite=Lax" in sess and "Max-Age=1209600" in sess and "Path=/" in sess
    assert "Secure" not in sess  # development switch off
    assert who(client)
    site.clock.advance(hours=2)
    site.login(site.client())
    (u,) = site.rows("SELECT last_login_at, prev_login_at FROM users WHERE role='student'")
    assert u["prev_login_at"] == "2026-10-10T12:00:00Z" and u["last_login_at"] == "2026-10-10T14:00:00Z"


def test_login_with_open_redirect_next_goes_home(site, client):
    site.signup(site.client())
    for bad in ("//evil.com", "/\\evil.com", "https://evil.com", "/%2fevil.com"):
        assert site.login(site.client(), next=bad).headers["location"] == "/"


def test_login_failures_are_generic_and_identical_for_unknown_email_and_wrong_password(site, client):
    site.signup(site.client())
    wrong = site.login(client, password="not-the-password")
    unknown = site.login(client, email="nobody@example.com")
    assert wrong.status_code == unknown.status_code == 401
    strip = lambda t: re.sub(r'value="[^"]*"', "", t)
    assert strip(wrong.text) == strip(unknown.text) and "do not match" in wrong.text
    assert "exist" not in wrong.text.lower() and not who(client)
    assert not any(c.startswith("session=") for c in unknown.headers.get_list("set-cookie"))


def test_unknown_email_still_pays_for_a_scrypt_verify(site, client, monkeypatch):
    calls = []
    import classbook.routes.accounts as acc
    real = acc.verify_password
    monkeypatch.setattr(acc, "verify_password", lambda p, h: calls.append(h) or real(p, h))
    site.login(client, email="nobody@example.com")
    assert calls == [acc.dummy_hash()]


def test_login_needs_csrf_and_rotates_it(site, client):
    site.signup(site.client())
    before = site.csrf(client)
    r = site.login(client, csrf_token=before)
    after = client.cookies.get("csrf")
    assert after and after != before and any(c.startswith("csrf=") for c in r.headers.get_list("set-cookie"))
    assert client.post("/logout", data={"csrf_token": before}, follow_redirects=False).status_code == 403  # old token is dead


def test_logout_deletes_session_rotates_csrf_and_old_cookie_is_dead(site, client):
    site.signup(client)
    old_cookie, old_csrf = client.cookies.get("session"), client.cookies.get("csrf")
    r = client.post("/logout", data={"csrf_token": site.csrf(client)}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/"
    assert site.rows("SELECT * FROM sessions") == []
    assert any(c.startswith("session=;") or "Max-Age=0" in c for c in r.headers.get_list("set-cookie"))
    assert client.cookies.get("csrf") != old_csrf
    replay = TestClient(site.app)
    replay.cookies.set("session", old_cookie)
    assert not who(replay)
    assert replay.get("/login").status_code == 200


def test_logout_without_session_redirects_to_login(site, client):
    r = site.post(client, "/logout")
    assert r.status_code == 303 and r.headers["location"] == "/login"


# ---- cookies and sessions ----

def test_forged_garbage_and_expired_cookies_are_anonymous(site, client):
    site.signup(client)
    good = client.cookies.get("session")
    for bad in ("x" * 43, "garbage", good[:-1] + ("A" if good[-1] != "A" else "B"), "'; DROP TABLE sessions;--"):
        c = TestClient(site.app)
        c.cookies.set("session", bad)
        assert not who(c)
    site.clock.advance(days=14)
    assert not who(client)  # expired


def test_login_replaces_a_presented_session_token(site, client):
    site.signup(client)
    first = client.cookies.get("session")
    site.login(client)
    assert client.cookies.get("session") != first
    assert len(site.rows("SELECT * FROM sessions")) == 1  # presented one removed, new one stored (only hashes stored)


def test_session_cookie_is_host_prefixed_and_secure_in_production(env, tmp_path):
    prod = Site(env, APP_ENV="production", TRUSTED_PROXY_HOPS="1")
    c = prod.client()
    r = prod.signup(c)
    cookies = r.headers.get_list("set-cookie")
    sess = next(x for x in cookies if x.startswith("__Host-session="))
    assert "Secure" in sess and "HttpOnly" in sess and "Path=/" in sess and "Domain" not in sess
    assert any(x.startswith("__Host-csrf=") for x in cookies)
    assert who(c)


def test_pages_with_forms_are_no_store(site, client):
    for path in ("/login", "/signup"):
        assert client.get(path).headers["cache-control"] == "no-store"


# ---- throttles (T-4, T-18) ----

def fail(site, c, n, email="sam@example.com", xff=None, start=0):
    for i in range(n):
        site.login(c, email=email, password="bad-password-here",
                   headers={"X-Forwarded-For": xff(i + start)} if xff else None)


def test_per_email_cap_blocks_after_10_failures_even_with_right_password_and_a_new_ip(env):
    s = Site(env, TRUSTED_PROXY_HOPS="1")
    c = s.client()
    s.signup(s.client(), name="Sam")
    fail(s, c, 10, xff=lambda i: f"9.9.9.{i}")  # ten different IPs
    r = s.login(c, headers={"X-Forwarded-For": "7.7.7.7"})
    assert r.status_code == 429 and not who(c)
    page = c.post("/login", data={"csrf_token": s.csrf(c), "email": "sam@example.com", "password": PW},
                  headers={"X-Forwarded-For": "7.7.7.8"}, follow_redirects=False)
    assert page.status_code == 429 and "Too many attempts" in page.text and page.headers["retry-after"]
    s.clock.advance(minutes=16)
    assert s.login(c, headers={"X-Forwarded-For": "7.7.7.9"}).status_code == 303  # window passed


def test_per_email_cap_counts_unknown_emails_too(env):
    s = Site(env)
    c = s.client()
    fail(s, c, 10, email="ghost@example.com")
    assert s.login(c, email="ghost@example.com").status_code == 429


def test_per_ip_cap_20_failures_spread_over_many_emails(env):
    s = Site(env)
    c = s.client()
    for i in range(20):
        assert s.login(c, email=f"user{i}@example.com", password="bad-password-here").status_code == 401
    assert s.login(c, email="fresh@example.com").status_code == 429


def test_spoofed_x_forwarded_for_cannot_dodge_the_ip_cap(env):
    s = Site(env, TRUSTED_PROXY_HOPS="1")  # real proxy appends 5.5.5.5; client invents everything to its left
    c = s.client()
    for i in range(20):
        r = s.login(c, email=f"user{i}@example.com", password="bad-password-here",
                    headers={"X-Forwarded-For": f"1.1.1.{i}, 5.5.5.5"})
        assert r.status_code == 401
    spoofed = s.login(c, email="fresh@example.com", headers={"X-Forwarded-For": "2.2.2.2, 5.5.5.5"})
    assert spoofed.status_code == 429
    other_client = s.login(c, email="fresh@example.com", headers={"X-Forwarded-For": "6.6.6.6"})
    assert other_client.status_code == 401  # a genuinely different client address is not blocked


def test_with_zero_hops_the_forwarded_header_is_ignored(env):
    s = Site(env)  # TRUSTED_PROXY_HOPS=0
    c = s.client()
    for i in range(20):
        s.login(c, email=f"u{i}@example.com", headers={"X-Forwarded-For": f"8.8.8.{i}"})
    assert s.login(c, email="x@example.com", headers={"X-Forwarded-For": "4.4.4.4"}).status_code == 429


def test_signup_throttle_10_per_hour_per_ip(env):
    s = Site(env, TRUSTED_PROXY_HOPS="1")
    hdr = {"X-Forwarded-For": "1.2.3.4, 5.5.5.5"}
    for i in range(10):
        c = s.client()
        assert s.signup(c, email=f"u{i}@example.com", headers=hdr).status_code == 303
    r = s.signup(s.client(), email="u11@example.com", headers=hdr)
    assert r.status_code == 429 and "Too many attempts" in r.text
    assert s.signup(s.client(), email="u12@example.com", headers={"X-Forwarded-For": "1.2.3.4, 6.6.6.6"}).status_code == 303
    s.clock.advance(hours=1, seconds=1)
    assert s.signup(s.client(), email="u13@example.com", headers=hdr).status_code == 303


# ---- logging (password never logged) ----

def test_login_failure_log_line_has_no_email_or_password(env, capsys):
    s = Site(env)
    c = s.client()
    secret_email, secret_pw = "leaky.person@example.com", "super-secret-pw-12345"
    s.login(c, email=secret_email, password=secret_pw)
    s.signup(c, email=secret_email, password=secret_pw, name="Leaky Person")
    s.login(c, email=secret_email, password="another-wrong-pw-1")
    out = capsys.readouterr().out
    assert "login failed" in out and "signup ok" in out
    for needle in (secret_email, "leaky.person", secret_pw, "another-wrong-pw", "Leaky"):
        assert needle not in out


# ---- startup ----

def test_app_refuses_to_start_when_bootstrap_refuses(env, capsys):
    Site(env)
    with pytest.raises(SystemExit) as e:
        Site({**env, "ADMIN_EMAIL": "other@example.com"})
    assert e.value.code == 1
    assert "ADMIN_ALLOW_EMAIL_CHANGE" in capsys.readouterr().err


def test_admin_can_sign_in_with_env_password_and_gets_admin_role(site, client):
    r = site.login(client, email=GOOD_ENV["ADMIN_EMAIL"], password=GOOD_ENV["ADMIN_PASSWORD"])
    assert r.status_code == 303
    token = client.cookies.get("session")
    from classbook.auth.web import user_from_request  # lookup through the real seam
    req = type("R", (), {"cookies": {"session": token}, "app": site.app})()
    assert user_from_request(req).role == "admin"


def test_expired_sessions_are_purged_at_startup(env):
    s = Site(env)
    c = s.client()
    s.signup(c)
    later = FixedClock(NOW + timedelta(days=15))
    create_app(s.settings, later)
    assert s.rows("SELECT * FROM sessions") == []


# ---- shared pieces this task touches ----

def test_error_pages_for_429_and_503_are_readable(site, client):
    from fastapi import HTTPException

    @site.app.get("/t/429")
    def a(): raise HTTPException(429)

    @site.app.get("/t/503")
    def b(): raise HTTPException(503)
    assert "Too many attempts" in client.get("/t/429").text and "Please wait" in client.get("/t/429").text
    assert "We are busy" in client.get("/t/503").text and "Something went wrong" not in client.get("/t/503").text


def test_dockerfile_disables_uvicorn_proxy_headers():
    from pathlib import Path
    assert "--no-proxy-headers" in (Path(__file__).parent.parent / "Dockerfile").read_text()


def test_current_user_seam_can_still_be_overridden_by_other_tasks(site, client):
    from classbook.web.deps import User, current_user, require_admin
    from fastapi import Depends

    @site.app.get("/t/admin")
    def admin(u=Depends(require_admin)): return "ok"
    assert client.get("/t/admin", follow_redirects=False).status_code == 303
    site.app.dependency_overrides[current_user] = lambda: User(1, "m@example.com", "Maya", "admin")
    assert client.get("/t/admin").status_code == 200
