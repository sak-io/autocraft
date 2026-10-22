"""T7 (2): full authorisation matrix. Every route x {anonymous, student A (owner), student B (other), admin}.

Real sessions, real guards (no dependency overrides). Denied cells must also leave the database untouched:
the point of an authz test is "refused AND nothing changed".
"""
import re

import pytest

from tests.qa.support import TOKEN, one, rows
from tests.qa.test_route_guards import POLICY

ROLES = ("anon", "a", "b", "admin")
WHO = {"anon": None, "a": "a", "b": "b", "admin": "admin"}
NEW_CLASS = {"title": "New Class", "starts_at": "2026-11-20T10:00", "duration_min": "60",
             "instructor": "Maya", "capacity": "5"}
NO = "login"  # shorthand: 303 to the sign-in page


def build_matrix(ids):
    c1, bk = ids["c1"], ids["booking_a"]
    login_next = lambda path: (303, f"/login?next={path}")  # noqa: E731  (GET: carries where you were going)
    login_post = (303, "/login")                             # POST: no next
    same = lambda x: {r: x for r in ROLES}                   # noqa: E731
    return {
        ("GET", "/health"): ("GET", "/health", None, same(200)),
        ("GET", "/"): ("GET", "/", None, same(200)),
        ("GET", "/classes/{class_id}"): ("GET", f"/classes/{c1}", None, same(200)),
        ("GET", "/login"): ("GET", "/login", None, same(200)),
        ("GET", "/signup"): ("GET", "/signup", None, same(200)),
        ("POST", "/login"): ("POST", "/login", {"email": "nobody@example.com", "password": "wrong-password-123"}, same(401)),
        ("POST", "/signup"): ("POST", "/signup", {"name": "", "email": "x", "password": "short"}, same(422)),
        ("POST", "/logout"): ("POST", "/logout", {}, {"anon": login_post, "a": (303, "/"), "b": (303, "/"), "admin": (303, "/")}),
        ("POST", "/classes/{class_id}/book"): ("POST", f"/classes/{c1}/book", {},
                                               {"anon": login_post, "a": (303, "/my-bookings"), "b": (303, "/my-bookings"), "admin": 403}),
        ("GET", "/my-bookings"): ("GET", "/my-bookings", None,
                                  {"anon": login_next("/my-bookings"), "a": 200, "b": 200, "admin": 403}),
        ("POST", "/bookings/{booking_id}/cancel"): ("POST", f"/bookings/{bk}/cancel", {},
                                                    {"anon": login_post, "a": (303, "/my-bookings"), "b": 404, "admin": 403}),
        ("GET", "/admin/classes"): ("GET", "/admin/classes", None,
                                    {"anon": login_next("/admin/classes"), "a": 403, "b": 403, "admin": 200}),
        ("GET", "/admin/classes/new"): ("GET", "/admin/classes/new", None,
                                        {"anon": login_next("/admin/classes/new"), "a": 403, "b": 403, "admin": 200}),
        ("POST", "/admin/classes"): ("POST", "/admin/classes", NEW_CLASS,
                                     {"anon": login_post, "a": 403, "b": 403, "admin": (303, "/admin/classes/")}),
        ("GET", "/admin/classes/{class_id}"): ("GET", f"/admin/classes/{c1}", None,
                                               {"anon": login_next(f"/admin/classes/{c1}"), "a": 403, "b": 403, "admin": 200}),
        ("GET", "/admin/classes/{class_id}/edit"): ("GET", f"/admin/classes/{c1}/edit", None,
                                                    {"anon": login_next(f"/admin/classes/{c1}/edit"), "a": 403, "b": 403, "admin": 200}),
        ("POST", "/admin/classes/{class_id}"): ("POST", f"/admin/classes/{c1}", {**NEW_CLASS, "title": "Renamed"},
                                                {"anon": login_post, "a": 403, "b": 403, "admin": (303, f"/admin/classes/{c1}")}),
        ("POST", "/admin/classes/{class_id}/cancel"): ("POST", f"/admin/classes/{c1}/cancel", {},
                                                       {"anon": login_post, "a": 403, "b": 403, "admin": (303, f"/admin/classes/{c1}")}),
    }


def fingerprint(path):
    out = []
    for table in ("classes", "bookings", "users", "messages", "sessions"):
        out.append(rows(path, f"SELECT * FROM {table} ORDER BY 1"))
    return out


def test_matrix_covers_every_route_and_every_role(template_db):
    from tests.qa.support import build_template  # noqa: F401  (ids are set by the template fixture)
    matrix = build_matrix(build_template.ids)
    assert set(matrix) == set(POLICY), "authz matrix and route policy have drifted apart"
    assert all(set(v[3]) == set(ROLES) for v in matrix.values())


def _cases():
    # ids are only known once the template exists; build with placeholders, resolve in the test
    return [(key, role) for key in POLICY for role in ROLES]


@pytest.mark.parametrize("key,role", _cases(), ids=lambda v: v if isinstance(v, str) else f"{v[0]} {v[1]}")
def test_authz_matrix_cell(world, key, role):
    method, path, data, expected = build_matrix(world.ids)[key]
    browser = world.browser(WHO[role])
    before = fingerprint(world.path)
    resp = browser.post_form(path, data) if method == "POST" else browser.get(path)
    want = expected[role]
    status, loc = want if isinstance(want, tuple) else (want, None)
    assert resp.status_code == status, f"{role} {method} {path}: {resp.status_code} {resp.headers.get('location')}"
    if loc is not None:
        assert resp.headers["location"].startswith(loc), resp.headers["location"]
    denied = status in (401, 403, 404, 422) or (status == 303 and loc is not None and loc.startswith("/login"))
    if denied:
        assert fingerprint(world.path) == before, "a refused request changed data"
    if status == 403 or (status == 303 and loc and loc.startswith("/login")):
        for secret in ("a@example.com", "b@example.com", "Alice A", "Bob B", "maya@example.com"):
            assert secret not in resp.text, f"refusal leaks {secret}"


def test_allowed_admin_and_owner_cells_really_changed_something(world):
    """Guards against a matrix that 'passes' because nothing works: the allowed cells have effects."""
    admin = world.browser("admin")
    r = admin.post_form("/admin/classes", {"title": "Created", "starts_at": "2026-11-20T10:00", "duration_min": "60",
                                           "instructor": "Maya", "capacity": "5"})
    assert r.status_code == 303 and one(world.path, "SELECT COUNT(*) FROM classes WHERE title='Created'") == 1
    r = world.browser("a").post_form(f"/bookings/{world.ids['booking_a']}/cancel")
    assert r.status_code == 303
    assert one(world.path, "SELECT status FROM bookings WHERE id=?", world.ids["booking_a"]) == "cancelled"


@pytest.mark.parametrize("variant", ["no token", "token differs from cookie", "token only in header"])
@pytest.mark.parametrize("role", ROLES)
def test_every_post_route_rejects_a_missing_or_wrong_csrf_token(world, role, variant):
    """Rule applies before the guard: even an anonymous or forbidden caller gets 403 and nothing happens."""
    matrix = build_matrix(world.ids)
    browser = world.browser(WHO[role])
    before = fingerprint(world.path)
    for key in POLICY:
        method, path, data, _ = matrix[key]
        if method != "POST":
            continue
        browser.cookies.delete("csrf")
        headers = {}
        if variant == "no token":
            resp = browser.post(path, data=data)
        elif variant == "token differs from cookie":
            browser.cookies.set("csrf", TOKEN)
            resp = browser.post(path, data={**data, "csrf_token": "Z" * 43})
        else:
            browser.cookies.set("csrf", TOKEN)
            resp = browser.post(path, data=data, headers={"X-CSRF-Token": TOKEN, "csrf_token": TOKEN})
        assert resp.status_code == 403, f"{role} {variant} POST {path} -> {resp.status_code}"
    assert fingerprint(world.path) == before


def test_methods_a_route_does_not_declare_are_405_and_change_nothing(world):
    admin = world.browser("admin")
    before = fingerprint(world.path)
    paths = {re.sub(r"\{class_id\}", str(world.ids["c1"]), re.sub(r"\{booking_id\}", str(world.ids["booking_a"]), p))
             for (_, p) in POLICY}
    paths.add("/static/style.css")
    for path in sorted(paths):
        for method in ("PUT", "PATCH", "DELETE"):
            admin.cookies.delete("csrf")
            admin.cookies.set("csrf", TOKEN)
            resp = admin.request(method, path, data={"csrf_token": TOKEN})
            assert resp.status_code == 405, f"{method} {path} -> {resp.status_code}"
    assert fingerprint(world.path) == before


def test_foreign_and_nonexistent_bookings_are_indistinguishable_to_student_b(world):
    """No oracle for booking ids: another student's booking answers exactly like one that does not exist."""
    b = world.browser("b")
    strip = lambda html: re.sub(r'value="[^"]*"', "", html)  # noqa: E731  (csrf tokens differ per response)
    foreign = b.post_form(f"/bookings/{world.ids['booking_a']}/cancel")
    ghost = b.post_form("/bookings/987654/cancel")
    assert foreign.status_code == ghost.status_code == 404
    assert strip(foreign.text) == strip(ghost.text)
    assert one(world.path, "SELECT status FROM bookings WHERE id=?", world.ids["booking_a"]) == "booked"


def test_student_b_sweeping_every_booking_id_cancels_nothing_of_a(world):
    b = world.browser("b")
    for booking_id in range(1, 21):  # the 20-per-hour action cap is the (intended) limit on guessing
        assert b.post_form(f"/bookings/{booking_id}/cancel").status_code == 404
    over = b.post_form("/bookings/21/cancel")
    assert over.status_code == 429 and over.headers["retry-after"] == "3600"
    assert one(world.path, "SELECT COUNT(*) FROM bookings WHERE status='booked'") == 1


def test_only_the_admin_page_shows_the_roster_with_emails(world):
    c1 = world.ids["c1"]
    for who in (None, "a", "b"):
        html = world.browser(who).get(f"/classes/{c1}").text
        assert "a@example.com" not in html and "Alice A" not in html, who
    html = world.browser("admin").get(f"/admin/classes/{c1}").text
    assert "a@example.com" in html and "Alice A" in html


def test_student_a_sees_own_booking_and_student_b_sees_nothing_of_it(world):
    assert "Flow" in world.browser("a").get("/my-bookings").text
    html_b = world.browser("b").get("/my-bookings").text
    assert "Flow" not in html_b and "no upcoming bookings" in html_b


def test_the_admin_cannot_book_or_cancel_as_a_student(world):
    admin = world.browser("admin")
    assert admin.post_form(f"/classes/{world.ids['c1']}/book").status_code == 403
    assert admin.post_form(f"/bookings/{world.ids['booking_a']}/cancel").status_code == 403
    assert one(world.path, "SELECT COUNT(*) FROM bookings") == 1
