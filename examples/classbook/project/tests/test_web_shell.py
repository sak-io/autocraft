from classbook.web.middleware import CSP

CSP_LITERAL = "default-src 'self'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'"
import re

import pytest
from fastapi import Depends, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.testclient import TestClient
from jinja2 import ChoiceLoader, DictLoader

from classbook.app import create_app
from classbook.config import Settings
from classbook.web import flash, render, rotate_csrf
from classbook.web.deps import (User, current_user, optional_user, require_admin, require_student,
                                require_user, get_mailer)
from classbook.web.util import client_ip

PAGES = {
    "t_form.html": '{% extends "base.html" %}{% block content %}<form method="post" action="/t/post">{{ csrf_field() }}<button>Go</button></form>{% endblock %}',
    "t_plain.html": '{% extends "base.html" %}{% block content %}<p>hello</p>{% endblock %}',
}
TOKEN = re.compile(r'name="csrf_token" value="([^"]+)"')
STUDENT, ADMIN = User(1, "s@example.com", "Sam", "student"), User(2, "m@example.com", "Maya", "admin")


def build(env, **over):
    app = create_app(Settings.from_env({**env, **over}))
    env_ = app.state.templates.env
    env_.loader = ChoiceLoader([DictLoader(PAGES), env_.loader])

    @app.get("/t/form")
    def form(request: Request): return render(request, "t_form.html")

    @app.get("/t/plain")
    def plain(request: Request): return render(request, "t_plain.html")

    @app.post("/t/post")
    def post(): return PlainTextResponse("posted")

    @app.post("/t/rotate")
    def rot(request: Request):
        rotate_csrf(request)
        return PlainTextResponse("rotated")

    @app.get("/t/flash-set")
    def fset(request: Request):
        resp = RedirectResponse("/t/plain", status_code=303)
        flash(request, resp, "Booked <b>yoga</b>", "success")
        return resp

    @app.get("/t/ip")
    def ip(request: Request): return PlainTextResponse(client_ip(request))

    @app.get("/t/public")
    def pub(u=Depends(optional_user)): return PlainTextResponse(u.role if u else "anon")

    @app.get("/t/user")
    def usr(u=Depends(require_user)): return PlainTextResponse("ok")

    @app.get("/t/student")
    def stu(u=Depends(require_student)): return PlainTextResponse("ok")

    @app.get("/t/admin")
    def adm(u=Depends(require_admin)): return PlainTextResponse("ok")

    return app


@pytest.fixture
def app(env):
    return build(env)


@pytest.fixture
def client(app):
    return TestClient(app, follow_redirects=False)


def token_of(client):
    return TOKEN.search(client.get("/t/form").text).group(1)


# ---- CSRF ----
def test_post_without_any_cookie_or_token_is_403(client):
    assert client.post("/t/post", data={"x": "1"}).status_code == 403


def test_post_with_token_but_no_cookie_is_403(client):
    assert client.post("/t/post", data={"csrf_token": "A" * 43}).status_code == 403


def test_first_get_of_a_form_page_sets_cookie_and_embeds_same_token(client):
    r = client.get("/t/form")
    cookie = client.cookies.get("csrf")
    assert cookie and TOKEN.search(r.text).group(1) == cookie
    assert "HttpOnly" in r.headers["set-cookie"] and "SameSite=Lax" in r.headers["set-cookie"]


def test_valid_token_without_a_session_is_accepted(client):  # login/signup case
    assert client.post("/t/post", data={"csrf_token": token_of(client)}).text == "posted"


def test_wrong_token_and_missing_field_are_403(client):
    token_of(client)
    assert client.post("/t/post", data={"csrf_token": "B" * 43}).status_code == 403
    assert client.post("/t/post", data={"other": "x"}).status_code == 403
    assert client.post("/t/post", json={"csrf_token": client.cookies.get("csrf")}).status_code == 403


def test_token_in_query_string_or_header_does_not_count(client):
    t = token_of(client)
    assert client.post(f"/t/post?csrf_token={t}").status_code == 403
    assert client.post("/t/post", headers={"x-csrf-token": t}).status_code == 403


def test_malformed_cookie_is_ignored_and_replaced(client):
    bad = {"cookie": "csrf=short"}
    assert client.post("/t/post", data={"csrf_token": "short"}, headers=bad).status_code == 403
    r = client.get("/t/form", headers=bad)
    t = TOKEN.search(r.text).group(1)
    assert len(t) == 43 and client.cookies.get("csrf") == t


def test_cookie_is_not_reissued_when_already_valid(client):
    token_of(client)
    assert "set-cookie" not in client.get("/t/form").headers


def test_page_without_forms_sets_no_csrf_cookie_and_is_cacheable(client):
    r = client.get("/t/plain")
    assert "set-cookie" not in r.headers and "cache-control" not in r.headers


def test_rotation_issues_a_new_token_and_old_one_stops_working(client):
    old = token_of(client)
    r = client.post("/t/rotate", data={"csrf_token": old})
    new = client.cookies.get("csrf")
    assert r.status_code == 200 and new != old
    assert client.post("/t/post", data={"csrf_token": old}).status_code == 403
    assert client.post("/t/post", data={"csrf_token": new}).status_code == 200


def test_get_requests_need_no_token(client):
    assert client.get("/health").status_code == 200


def test_csrf_failure_page_has_no_internals_and_is_not_cached(client):
    r = client.post("/t/post", data={})
    assert "expired" in r.text and r.headers["cache-control"] == "no-store"


# ---- F22 ----
def test_every_page_with_a_csrf_token_is_no_store(client):
    assert client.get("/t/form").headers["cache-control"] == "no-store"   # first visit
    assert client.get("/t/form").headers["cache-control"] == "no-store"   # cookie already present


# ---- headers ----
HDRS = {"content-security-policy": CSP, "x-content-type-options": "nosniff",
        "x-frame-options": "DENY", "referrer-policy": "same-origin"}


@pytest.mark.parametrize("path,status", [("/health", 200), ("/t/form", 200), ("/nope", 404), ("/static/style.css", 200)])
def test_security_headers_on_every_response(client, path, status):
    r = client.get(path)
    assert r.status_code == status
    for k, v in HDRS.items():
        assert r.headers[k] == v
    assert "strict-transport-security" not in r.headers  # not in development/test


def test_headers_also_on_403_413_and_500(client, app):
    @app.get("/t/boom")
    def boom(): raise ValueError("x")
    for r in (client.post("/t/post"), client.post("/t/post", content=b"x" * 20000),
              TestClient(app, raise_server_exceptions=False).get("/t/boom")):
        assert r.headers["x-frame-options"] == "DENY" and r.headers["content-security-policy"] == CSP_LITERAL


def test_production_has_hsts_host_prefixed_secure_cookie(env):
    app = build(env, APP_ENV="production", TRUSTED_PROXY_HOPS="1")
    c = TestClient(app, base_url="https://testserver")
    r = c.get("/t/form")
    assert r.headers["strict-transport-security"].startswith("max-age=")
    sc = r.headers["set-cookie"]
    assert sc.startswith("__Host-csrf=") and "Secure" in sc and "Path=/" in sc and "Domain" not in sc and "HttpOnly" in sc
    assert c.post("/t/post", data={"csrf_token": TOKEN.search(r.text).group(1)}).status_code == 200


# ---- body limit ----
def test_body_over_16kb_is_413_even_with_valid_csrf(client):
    t = token_of(client)
    r = client.post("/t/post", data={"csrf_token": t, "pad": "x" * 17000})
    assert r.status_code == 413


def test_body_exactly_16kb_is_allowed(client):
    t = token_of(client)
    body = f"csrf_token={t}&pad=" 
    body += "x" * (16 * 1024 - len(body))
    assert len(body) == 16 * 1024
    r = client.post("/t/post", content=body, headers={"content-type": "application/x-www-form-urlencoded"})
    assert r.status_code == 200


def test_chunked_body_over_limit_is_413(client):
    def gen():
        for _ in range(5):
            yield b"x" * 5000
    assert client.post("/t/post", content=gen(), headers={"content-type": "application/x-www-form-urlencoded"}).status_code == 413


# ---- flash ----
def test_flash_is_shown_once_escaped_then_cleared(client):
    r = client.get("/t/flash-set")
    assert r.status_code == 303
    page = client.get("/t/plain")
    assert "Booked &lt;b&gt;yoga&lt;/b&gt;" in page.text and "<b>yoga</b>" not in page.text
    assert 'class="flash success"' in page.text and page.headers["cache-control"] == "no-store"
    assert "flash" not in client.cookies
    assert "Booked" not in client.get("/t/plain").text


def test_garbage_flash_cookie_is_ignored(client):
    client.cookies.set("flash", "!!!not-base64!!!")
    r = client.get("/t/plain")
    assert r.status_code == 200 and 'class="flash' not in r.text


# ---- guards ----
def test_default_seam_means_nobody_is_signed_in(client):
    assert client.get("/t/public").text == "anon"
    r = client.get("/t/student")
    assert r.status_code == 303 and r.headers["location"] == "/login?next=/t/student"
    assert client.get("/t/admin").headers["location"] == "/login?next=/t/admin"


def test_guard_redirect_for_post_has_no_next(app):
    @app.post("/t/guarded")
    def g(u=Depends(require_student)): return PlainTextResponse("ok")
    c = TestClient(app, follow_redirects=False)
    t = TOKEN.search(c.get("/t/form").text).group(1)
    r = c.post("/t/guarded", data={"csrf_token": t})
    assert r.status_code == 303 and r.headers["location"] == "/login"


@pytest.mark.parametrize("user,path,status", [
    (STUDENT, "/t/student", 200), (STUDENT, "/t/admin", 403), (STUDENT, "/t/user", 200),
    (ADMIN, "/t/admin", 200), (ADMIN, "/t/student", 403), (ADMIN, "/t/user", 200),
])
def test_roles_can_be_supplied_by_dependency_override(app, user, path, status):
    app.dependency_overrides[current_user] = lambda: user
    r = TestClient(app, follow_redirects=False).get(path)
    assert r.status_code == status
    assert r.headers["cache-control"] == "no-store"  # authenticated pages


def test_403_page_is_html_and_public_page_for_signed_in_user_is_no_store(app):
    app.dependency_overrides[current_user] = lambda: STUDENT
    c = TestClient(app)
    assert "text/html" in c.get("/t/admin").headers["content-type"]
    assert c.get("/t/public").headers["cache-control"] == "no-store"


def test_nav_follows_the_user(app):
    c = TestClient(app)
    assert "Sign in" in c.get("/nope").text
    app.dependency_overrides[current_user] = lambda: ADMIN
    page = c.get("/t/student").text  # the 403 page is rendered with the signed-in admin
    assert "Manage classes" in page and "Sign out" in page and 'name="csrf_token"' in page


# ---- factory / seams ----
def test_proxy_ip_through_the_app(env):
    c = TestClient(build(env, APP_ENV="development", TRUSTED_PROXY_HOPS="1"))
    assert c.get("/t/ip", headers={"x-forwarded-for": "9.9.9.9, 203.0.113.7"}).text == "203.0.113.7"
    c0 = TestClient(build(env))
    assert c0.get("/t/ip", headers={"x-forwarded-for": "9.9.9.9"}).text == "testclient"


def test_routers_are_registered_by_the_factory(app):
    from classbook.routes import ROUTERS, accounts, bookings, classes
    assert ROUTERS == [accounts.router, classes.router, bookings.router]
    assert accounts.router.routes and bookings.router.routes  # classes joins when T4 merges


def test_mailer_protocol_seam_is_on_app_state(app):
    class Fake:
        def send(self, to, subject, body): self.got = (to, subject, body)
    app.state.mailer = Fake()
    class R:  # minimal request stand-in
        pass
    r = R(); r.app = app
    get_mailer(r).send("a@b.c", "s", "b")
    assert app.state.mailer.got == ("a@b.c", "s", "b")
