"""T7 (4): the whole journey over real HTTP, like a person with a browser (cookies and the server's own CSRF
tokens, no test shortcuts): visitor -> class page -> sign in with `next` -> book -> my bookings -> cancel ->
admin roster -> admin cancels the class -> emails recorded as expected."""
import re

from tests.e2e.conftest import real_at, sign_in
from tests.qa.support import ADMIN_EMAIL, ADMIN_PASSWORD, PASSWORD, csrf_in, insert_class, insert_user, one, rows

EMAIL, NAME = "priya@example.com", "Priya Patel"


def seed(conn, ids):
    insert_user(conn, EMAIL, NAME, password=PASSWORD)
    ids["near"] = insert_class(conn, real_at(days=3), 2, "Morning Flow", "Maya")
    ids["far"] = insert_class(conn, real_at(days=45), 5, "Far Yoga", "Tom")
    ids["beyond"] = insert_class(conn, real_at(days=75), 5, "Way Later", "Tom")
    ids["cancelled"] = insert_class(conn, real_at(days=5), 5, "Called Off", "Tom", status="cancelled")
    ids["past"] = insert_class(conn, real_at(days=-2), 5, "Yesterday Class", "Tom")


def form_action(html, contains):
    return re.search(rf'<form method="post" action="([^"]*{contains}[^"]*)"', html).group(1)


def test_visitor_to_booking_to_cancel_to_admin_roster_to_studio_cancel(live):
    ids = {}
    server = live(lambda conn: seed(conn, ids))
    near = ids["near"]

    # 1. a visitor sees the schedule: bookable class, greyed class with opens-on date, nothing else
    visitor = server.client()
    home = visitor.get("/")
    assert home.status_code == 200
    assert "Morning Flow" in home.text and "2 spots left" in home.text
    assert "Far Yoga" in home.text and 'data-state="opens_later"' in home.text and "Opens for booking on" in home.text
    for hidden in ("Way Later", "Called Off", "Yesterday Class"):
        assert hidden not in home.text
    assert home.text.index("Morning Flow") < home.text.index("Far Yoga")  # ordered by start time

    # 2. class page: no Book form, a "Sign in to book" link that carries where to come back to
    page = visitor.get(f"/classes/{near}")
    assert f'href="/login?next=/classes/{near}"' in page.text and "/book" not in page.text
    assert page.headers["cache-control"] == "no-store"

    # 3. follow the link: the form keeps `next`; a wrong password is a generic 401
    login = visitor.get(f"/login?next=/classes/{near}")
    assert f'name="next" value="/classes/{near}"' in login.text
    bad = visitor.post("/login", data={"csrf_token": csrf_in(login.text), "email": EMAIL, "password": "wrong-password",
                                       "next": f"/classes/{near}"})
    assert bad.status_code == 401 and "do not match" in bad.text and "session" not in visitor.cookies

    # 4. right password -> back on the class (AC-2.3), with an HttpOnly session cookie
    login = visitor.get(f"/login?next=/classes/{near}")
    ok = visitor.post("/login", data={"csrf_token": csrf_in(login.text), "email": EMAIL, "password": PASSWORD,
                                      "next": f"/classes/{near}"})
    assert ok.status_code == 303 and ok.headers["location"] == f"/classes/{near}"
    cookie_header = " ".join(ok.headers.get_list("set-cookie")).lower()
    assert "httponly" in cookie_header and "samesite=lax" in cookie_header
    page = visitor.get(f"/classes/{near}")
    action = form_action(page.text, "/book")
    assert action == f"/classes/{near}/book"

    # 5. book (AC-3.1): redirected to My bookings with a message; spots drop to 1
    booked = visitor.post(action, data={"csrf_token": csrf_in(page.text)})
    assert booked.status_code == 303 and booked.headers["location"] == "/my-bookings"
    mine = visitor.get("/my-bookings")
    assert "Booked: Morning Flow" in mine.text and "Cancel booking" in mine.text
    assert "1 spot left" in server.client().get("/").text

    # 6. double click / back-button resubmit: still one booking
    again = visitor.post(action, data={"csrf_token": csrf_in(page.text)})
    assert again.status_code == 303
    assert "already booked" in visitor.get("/my-bookings").text
    assert one(server.path, "SELECT COUNT(*) FROM bookings WHERE status='booked'") == 1
    assert server.wait_for(lambda: one(server.path, "SELECT COUNT(*) FROM messages WHERE status='recorded'") == 1)

    # 7. cancel (AC-4.2): spot comes back; resubmitting the cancel is a harmless no-op (AC-4.5)
    mine = visitor.get("/my-bookings")
    cancel_action = form_action(mine.text, "/cancel")
    done = visitor.post(cancel_action, data={"csrf_token": csrf_in(mine.text)})
    assert done.status_code == 303
    after = visitor.get("/my-bookings")
    assert "Cancelled: Morning Flow" in after.text and "no upcoming bookings" in after.text
    assert "2 spots left" in server.client().get("/").text
    repeat = visitor.post(cancel_action, data={"csrf_token": csrf_in(after.text)})
    assert repeat.status_code == 303 and "already cancelled" in visitor.get("/my-bookings").text
    assert server.wait_for(lambda: one(server.path, "SELECT COUNT(*) FROM messages WHERE status='recorded'") == 2)

    # 8. book again, then sign out: private pages are closed again
    page = visitor.get(f"/classes/{near}")
    visitor.post(f"/classes/{near}/book", data={"csrf_token": csrf_in(page.text)})
    assert server.wait_for(lambda: one(server.path, "SELECT COUNT(*) FROM messages WHERE status='recorded'") == 3)
    out = visitor.post("/logout", data={"csrf_token": csrf_in(visitor.get("/").text)})
    assert out.status_code == 303 and out.headers["location"] == "/"
    gone = visitor.get("/my-bookings")
    assert gone.status_code == 303 and gone.headers["location"].startswith("/login")

    # 9. admin: sees the roster with name and email, and spots left (AC-6.1)
    admin = sign_in(server, ADMIN_EMAIL, ADMIN_PASSWORD, next="/admin/classes")
    listing = admin.get("/admin/classes")
    assert listing.status_code == 200 and "Morning Flow" in listing.text and "Not open yet" in listing.text
    detail = admin.get(f"/admin/classes/{near}")
    assert f"{NAME} ({EMAIL})" in detail.text and "booked 1" in detail.text and "spots left 1" in detail.text

    # 10. the admin cancels the class (AC-6.3): confirmation says students are NOT emailed
    cancel_class = admin.post(f"/admin/classes/{near}/cancel", data={"csrf_token": csrf_in(detail.text)})
    assert cancel_class.status_code == 303
    flash = admin.get(f"/admin/classes/{near}")
    assert "Class cancelled" in flash.text and "not emailed" in flash.text
    assert "Nobody is booked" in flash.text

    # 11. the student signs in again: the booking is shown "cancelled by the studio", no cancel button, not on the schedule
    student = sign_in(server, EMAIL, PASSWORD)
    mine = student.get("/my-bookings")
    assert "Cancelled by the studio" in mine.text and "Cancel booking" not in mine.text
    assert "Morning Flow" not in student.get("/").text
    assert "cancelled by the studio" in student.get(f"/classes/{near}").text
    refused = student.post(f"/classes/{near}/book", data={"csrf_token": csrf_in(student.get("/").text)})
    assert refused.status_code == 409 and "already started or has been cancelled" in refused.text

    # 12. emails: booked, cancelled, booked (rebook) to the student; NOTHING for the studio cancel
    assert server.wait_for(lambda: one(server.path, "SELECT COUNT(*) FROM messages WHERE status='pending'") == 0)
    msgs = rows(server.path, "SELECT to_email, kind, status, subject, body FROM messages ORDER BY id")
    assert [(m[0], m[1], m[2]) for m in msgs] == [(EMAIL, "booked", "recorded"), (EMAIL, "cancelled", "recorded"),
                                                   (EMAIL, "booked", "recorded")]
    for to, kind, status, subject, body in msgs:
        assert "Morning Flow" in subject and kind in subject and "Morning Flow" in body and kind in body
        assert re.search(r"\b\d{2} \w{3} \d{4}, \d{2}:\d{2} \(London time\)", body)
        assert NAME not in body and EMAIL not in body  # T-17: nothing the student chose is echoed
    final = rows(server.path, "SELECT status, cancelled_by FROM bookings ORDER BY id")
    assert final == [("cancelled", "student"), ("cancelled", "studio")]

    # 13. the admin sees the previous sign-in on the next visit (AR-1 mitigation)
    again = sign_in(server, ADMIN_EMAIL, ADMIN_PASSWORD)
    assert "Your previous sign-in" in again.get("/admin/classes").text

    # 14. the server log: no crash, and no secret or personal data
    log = server.log
    assert "Traceback" not in log and "unhandled exception" not in log
    for private in (PASSWORD, ADMIN_PASSWORD, EMAIL, NAME, ADMIN_EMAIL, "wrong-password"):
        assert private not in log, f"{private!r} leaked into the server log"


def test_sign_up_with_next_signs_in_and_lands_on_the_class_then_a_duplicate_is_generic(live):
    ids = {}
    server = live(lambda conn: seed(conn, ids))
    near = ids["near"]
    visitor = server.client()
    form = visitor.get(f"/signup?next=/classes/{near}")
    new = visitor.post("/signup", data={"csrf_token": csrf_in(form.text), "name": "Zoë 瑜伽", "email": "ZOE@Example.com",
                                        "password": "pässword-with-ünicode-1", "next": f"/classes/{near}"})
    assert new.status_code == 303 and new.headers["location"] == f"/classes/{near}"
    assert "Book" in visitor.get(f"/classes/{near}").text
    assert rows(server.path, "SELECT email, name, role FROM users WHERE name LIKE 'Zo%'") == [("zoe@example.com", "Zoë 瑜伽", "student")]
    # same email again (different case): generic message, no second account, nothing says "already registered"
    other = server.client()
    form = other.get("/signup")
    dup = other.post("/signup", data={"csrf_token": csrf_in(form.text), "name": "Someone", "email": "zoe@EXAMPLE.com",
                                      "password": "another-long-password"})
    assert dup.status_code == 422 and "could not create an account with these details" in dup.text.lower()
    assert "already registered" not in dup.text.lower() and "exists" not in dup.text.lower() and one(server.path, "SELECT COUNT(*) FROM users WHERE email='zoe@example.com'") == 1
    # and the new account can sign in with the unicode password later
    assert sign_in(server, "zoe@example.com", "pässword-with-ünicode-1").get("/my-bookings").status_code == 200


def test_production_mode_over_real_http_sets_host_prefixed_secure_cookies_and_hsts(live):
    """APP_ENV=production behind one proxy hop. Plain http here, so cookies are handled by hand (a browser
    would only ever see https from the host's proxy)."""
    ids = {}
    server = live(lambda conn: seed(conn, ids),
                  env={"APP_ENV": "production", "TRUSTED_PROXY_HOPS": "1"})
    c = server.client()
    r = c.get("/login", headers={"X-Forwarded-For": "6.6.6.6, 203.0.113.9"})
    assert r.headers["strict-transport-security"].startswith("max-age=")
    csrf_cookie = [h for h in r.headers.get_list("set-cookie") if h.startswith("__Host-csrf=")][0]
    assert "Secure" in csrf_cookie and "HttpOnly" in csrf_cookie and "Path=/" in csrf_cookie and "Domain" not in csrf_cookie
    token = csrf_cookie.split("=", 1)[1].split(";", 1)[0]
    c.cookies.clear()
    ok = c.post("/login", data={"csrf_token": token, "email": EMAIL, "password": PASSWORD},
                headers={"Cookie": f"__Host-csrf={token}"})
    assert ok.status_code == 303
    session_cookie = [h for h in ok.headers.get_list("set-cookie") if h.startswith("__Host-session=")][0]
    assert "Secure" in session_cookie and "HttpOnly" in session_cookie and "SameSite=Lax" in session_cookie
    value = session_cookie.split("=", 1)[1].split(";", 1)[0]
    mine = c.get("/my-bookings", headers={"Cookie": f"__Host-session={value}"})
    assert mine.status_code == 200 and mine.headers["cache-control"] == "no-store"
    assert c.get("/my-bookings", headers={"Cookie": f"session={value}"}).status_code == 303  # unprefixed name is not accepted
