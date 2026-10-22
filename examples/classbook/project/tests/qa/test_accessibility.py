"""T7 (5): accessibility checks on the HTML ClassBook really serves (roles x states), plus the stylesheet.

Automated checks catch about a third of accessibility problems; the rest is the manual keyboard/phone
checklist in docs/qa/qa-summary.md. What is checked here: page language, one h1, a title, labelled inputs,
unique ids, heading order, skip link target, buttons/links with names, readable throttle/busy/error pages,
visible focus, colour contrast (all colour pairs, both themes), tap-target size, zoomable viewport.
"""
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

from classbook.kernel import db
from tests.qa.support import TOKEN, insert_booking, insert_class, insert_user, session_for

CSS = (Path(__file__).resolve().parents[2] / "classbook/web/static/style.css").read_text()


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.lang = None
        self.title = ""
        self.headings = []        # (level, text)
        self.ids = []
        self.labels_for = []
        self.aria_labels = {}     # id -> label
        self.controls = []        # (tag, attrs)
        self.metas = []
        self.links = []           # (href, text)
        self.buttons = []         # text
        self.forms = []
        self.main = 0
        self.nav_labels = []
        self.describedby = []
        self.ths = []
        self._stack = []
        self._text = {}
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "html":
            self.lang = a.get("lang")
        elif tag == "meta":
            self.metas.append(a)
        elif tag in ("h1", "h2", "h3", "h4", "title", "a", "button", "label"):
            self._stack.append([tag, a, ""])
        elif tag == "label" and "for" in a:
            self.labels_for.append(a["for"])
        elif tag in ("input", "select", "textarea"):
            self.controls.append((tag, a))
        elif tag == "form":
            self.forms.append(a)
        elif tag == "main":
            self.main += 1
        elif tag == "nav":
            self.nav_labels.append(a.get("aria-label"))
        elif tag == "th":
            self.ths.append(a)
        if "aria-describedby" in a:
            self.describedby.append(a["aria-describedby"])

    def handle_data(self, data):
        for item in self._stack:
            item[2] += data

    def handle_endtag(self, tag):
        for i in range(len(self._stack) - 1, -1, -1):
            if self._stack[i][0] == tag:
                t, a, text = self._stack.pop(i)
                text = " ".join(text.split())
                if t == "title":
                    self.title = text
                elif t.startswith("h"):
                    self.headings.append((int(t[1]), text))
                elif t == "a":
                    self.links.append((a.get("href"), text))
                elif t == "button":
                    self.buttons.append(text)
                elif t == "label":
                    if "for" in a:
                        self.labels_for.append(a["for"])
                break


def check_common(html, name, full=True):
    p = Page(html)
    assert p.lang == "en", f"{name}: <html lang> missing"
    assert p.title.strip(), f"{name}: empty <title>"
    assert any("charset" in m for m in p.metas), f"{name}: no charset"
    h1 = [t for lvl, t in p.headings if lvl == 1]
    assert len(h1) == 1 and h1[0], f"{name}: expected exactly one non-empty h1, got {h1}"
    levels = [lvl for lvl, _ in p.headings]
    assert levels[0] == 1 and all(b - a <= 1 for a, b in zip(levels, levels[1:])), f"{name}: heading order {levels}"
    assert len(p.ids) == len(set(p.ids)), f"{name}: duplicate ids {sorted(i for i in p.ids if p.ids.count(i) > 1)}"
    for target in p.describedby:
        assert target in p.ids, f"{name}: aria-describedby points at missing id {target}"
    visible = [(t, a) for t, a in p.controls if a.get("type") not in ("hidden", "submit", "button")]
    for tag, a in visible:
        assert a.get("id") in p.labels_for or a.get("aria-label"), f"{name}: input {a.get('name')} has no label"
    for f in p.labels_for:
        assert f in p.ids, f"{name}: <label for={f}> points at nothing"
    assert all(b for b in p.buttons), f"{name}: a button has no text"
    assert all(text for href, text in p.links), f"{name}: a link has no text: {[l for l in p.links if not l[1]]}"
    assert all(f.get("method") == "post" for f in p.forms), f"{name}: every form here is a POST form"
    assert all(a.get("scope") for a in p.ths), f"{name}: table header without scope"
    if full:
        vp = [m.get("content", "") for m in p.metas if m.get("name") == "viewport"]
        assert vp and "width=device-width" in vp[0], f"{name}: no responsive viewport"
        assert "user-scalable=no" not in vp[0] and "maximum-scale" not in vp[0], f"{name}: zoom is blocked"
        assert p.main == 1 and "main" in p.ids, f"{name}: needs exactly one <main id=main>"
        assert ("#main" in [h for h, _ in p.links]), f"{name}: skip link missing"
        assert p.nav_labels == ["Main"], f"{name}: nav needs a label"
    return p


@pytest.fixture(scope="module")
def a11y_world(template_db, tmp_path_factory):
    from tests.qa.support import copy_world
    return copy_world(template_db, tmp_path_factory.mktemp("a11y"))


@pytest.fixture(scope="module")
def pages(a11y_world):
    """name -> (status, html, response) for every kind of page, as the roles that see them (built once)."""
    world = a11y_world
    ids = world.ids
    with db.write_tx(world.path) as conn:
        ids["c"] = insert_user(conn, "c@example.com", "Cleo C")
        insert_booking(conn, insert_class(conn, "2026-10-14T10:00:00Z", 3, "Studio Called Off"), ids["b"])
        conn.execute("UPDATE classes SET status='cancelled' WHERE title='Studio Called Off'")
        conn.execute("UPDATE bookings SET status='cancelled', cancelled_by='studio', cancelled_at='2026-10-10T12:00:00Z' "
                     "WHERE user_id=?", (ids["b"],))
        soon = insert_class(conn, "2026-10-10T20:00:00Z", 3, "Tonight")        # within 12 h: cancel refused
        insert_booking(conn, soon, ids["b"])
    out = {}

    def grab(name, resp):
        out[name] = (resp.status_code, resp.text, resp)

    anon, a, b, admin = (world.browser(w) for w in (None, "a", "b", "admin"))
    grab("schedule", anon.get("/"))
    grab("class bookable (visitor)", anon.get(f"/classes/{ids['c1']}"))
    grab("class opens later", anon.get(f"/classes/{ids['c2']}"))
    grab("class cancelled", anon.get(f"/classes/{ids['c3']}"))
    grab("class (student, book button)", b.get(f"/classes/{ids['c1']}"))
    grab("class (booked student)", a.get(f"/classes/{ids['c1']}"))
    grab("login", anon.get("/login?next=/classes/1"))
    grab("login failed 401", anon.post_form("/login", {"email": "a@example.com", "password": "nope-nope-nope"}))
    grab("signup", anon.get("/signup"))
    grab("signup invalid 422", anon.post_form("/signup", {"name": "", "email": "bad", "password": "short"}))
    grab("my bookings", b.get("/my-bookings"))
    c_browser = world.browser(None)
    c_browser.cookies.set("session", session_for(world.path, ids["c"]))
    grab("my bookings empty", c_browser.get("/my-bookings"))
    grab("404", anon.get("/nope"))
    grab("405", anon.get("/logout"))
    grab("403 student on admin", a.get("/admin/classes"))
    grab("409 refused (cancelled class)", b.post_form(f"/classes/{ids['c3']}/book"))
    grab("409 too late to cancel", b.post_form(f"/bookings/{one_booking(world, 'Tonight')}/cancel"))
    grab("admin list", admin.get("/admin/classes"))
    grab("admin new", admin.get("/admin/classes/new"))
    grab("admin new invalid 422", admin.post_form("/admin/classes", {"title": "", "starts_at": "x", "duration_min": "0",
                                                                      "instructor": "", "capacity": "0"}))
    grab("admin detail (roster)", admin.get(f"/admin/classes/{ids['c1']}"))
    grab("admin edit", admin.get(f"/admin/classes/{ids['c1']}/edit"))
    grab("admin edit cancelled 409", admin.get(f"/admin/classes/{ids['c3']}/edit"))
    # throttles: 429 on login (10 failures on one email) and on booking (21st action in an hour)
    t = world.browser(None)
    for _ in range(10):
        t.post_form("/login", {"email": "victim@example.com", "password": "wrong-wrong-wrong"})
    grab("429 login", t.post_form("/login", {"email": "victim@example.com", "password": "wrong-wrong-wrong"}))
    c = world.browser("b")
    for _ in range(20):
        c.post_form(f"/classes/{ids['c3']}/book")
    grab("429 booking", c.post_form(f"/classes/{ids['c3']}/book"))
    return out


def one_booking(world, title):
    from tests.qa.support import one
    return one(world.path, "SELECT b.id FROM bookings b JOIN classes c ON c.id=b.class_id WHERE c.title=?", title)


EXPECTED_STATUS = {"schedule": 200, "class bookable (visitor)": 200, "class opens later": 200, "class cancelled": 200,
                   "class (student, book button)": 200, "class (booked student)": 200, "login": 200, "login failed 401": 401,
                   "signup": 200, "signup invalid 422": 422, "my bookings": 200, "my bookings empty": 200, "404": 404, "405": 405,
                   "403 student on admin": 403, "409 refused (cancelled class)": 409, "409 too late to cancel": 409,
                   "admin list": 200, "admin new": 200, "admin new invalid 422": 422, "admin detail (roster)": 200,
                   "admin edit": 200, "admin edit cancelled 409": 409, "429 login": 429, "429 booking": 429}


def test_every_page_state_returns_the_expected_status(pages):
    got = {k: v[0] for k, v in pages.items() if k in EXPECTED_STATUS}
    assert got == EXPECTED_STATUS


@pytest.mark.parametrize("name", sorted(EXPECTED_STATUS))
def test_page_is_structurally_accessible(pages, name):
    status, html, _ = pages[name]
    check_common(html, f"{name} ({status})")


def test_error_pages_use_plain_words_and_never_show_internals(pages):
    for name in ("404", "405", "403 student on admin", "409 refused (cancelled class)", "409 too late to cancel",
                 "429 login", "429 booking", "admin edit cancelled 409"):
        text = " ".join(Page(pages[name][1]).__dict__["title"].split()) + pages[name][1]
        for jargon in ("Traceback", "Exception", "sqlite", "IntegrityError", "HTTPException", "detail", "{"):
            assert jargon not in text, f"{name} shows {jargon!r}"


def test_throttle_pages_tell_people_to_wait_and_carry_retry_after(pages):
    st, html, resp = pages["429 login"]
    assert "Too many attempts" in html and "wait" in html.lower() and resp.headers["retry-after"] == "900"
    st, html, resp = pages["429 booking"]
    assert "Too many requests" in html and "try again later" in html and resp.headers["retry-after"] == "3600"


def test_refusal_pages_explain_why_and_offer_a_way_forward(pages):
    for name, phrase in (("409 refused (cancelled class)", "cancelled"), ("409 too late to cancel", "12 hours")):
        html = pages[name][1]
        assert phrase in html and 'href="/"' in html, name


def test_greyed_classes_say_so_in_words_not_only_in_colour(pages):
    html = pages["schedule"][1]
    assert re.search(r'data-state="opens_later".*?Opens for booking on', html, re.S)
    assert "Opens for booking on" in pages["class opens later"][1]


def test_studio_cancelled_bookings_say_so_in_words(pages):
    assert "Cancelled by the studio" in pages["my bookings"][1]


def test_form_errors_are_in_text_next_to_the_field_and_linked(pages):
    html = pages["admin new invalid 422"][1]
    p = check_common(html, "admin invalid")
    assert 'aria-invalid="true"' in html and html.count('class="error"') >= 4
    html = pages["signup invalid 422"][1]
    assert 'aria-describedby="name-err"' in html and 'id="name-err"' in html


# ---- busy / unexpected-error / expired-form pages (bare HTML, no site chrome) -----------------------------------
def bare_pages(world, monkeypatch):
    from fastapi.testclient import TestClient
    out = {}
    student = world.browser("b")  # its session must exist before the lock is taken
    real = db.write_tx
    monkeypatch.setattr(db, "write_tx", lambda p, ms=50: real(p, ms))
    holder = db.connect(world.path)
    holder.execute("BEGIN IMMEDIATE")
    try:
        out["503 busy"] = student.post_form(f"/classes/{world.ids['c1']}/book")
    finally:
        holder.execute("ROLLBACK")
        holder.close()
    out["403 form expired (csrf)"] = world.browser("b").post(f"/classes/{world.ids['c1']}/book", data={})
    big = world.browser("b")
    big.cookies.set("csrf", TOKEN)
    out["413 too large"] = big.post("/login", data={"csrf_token": TOKEN, "email": "x" * 20000, "password": "y"})

    def boom():
        raise RuntimeError("secret internal detail")

    world.app.add_api_route("/boom", boom)
    out["500"] = TestClient(world.app, raise_server_exceptions=False).get("/boom")
    return out


def test_busy_expired_form_toolarge_and_crash_pages_are_readable_and_say_what_to_do(world, monkeypatch):
    got = bare_pages(world, monkeypatch)
    assert {k: r.status_code for k, r in got.items()} == {"503 busy": 503, "403 form expired (csrf)": 403,
                                                          "413 too large": 413, "500": 500}
    for name, r in got.items():
        check_common(r.text, name, full=False)
        low = r.text.lower()
        assert "secret internal detail" not in low and "traceback" not in low
        assert re.search(r"try again|reload|send less", low), f"{name}: does not say what to do next"
    assert got["503 busy"].headers["retry-after"] == "5"


def test_bare_error_pages_have_a_viewport_meta_for_phones(world, monkeypatch):
    for name, r in bare_pages(world, monkeypatch).items():
        assert 'name="viewport"' in r.text, f"{name}: no viewport meta"


# ---- stylesheet --------------------------------------------------------------------------------------------------
def luminance(hex_):
    h = hex_.lstrip("#")
    rgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def ratio(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def themes():
    def parse(block):
        out = {}
        for k, v in re.findall(r"--([a-z]+):\s*(#[0-9a-fA-F]{3,6})\b", block):
            out[k] = "#" + "".join(c * 2 for c in v[1:]) if len(v) == 4 else v
        return out

    light = parse(CSS.split("@media")[0])
    dark = {**light, **parse(re.search(r"@media \(prefers-color-scheme: dark\) \{ :root \{([^}]*)\}", CSS).group(1))}
    return {"light": light, "dark": dark}


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_every_text_colour_meets_wcag_aa_on_the_background_in_both_themes(theme):
    t = themes()[theme]
    for name in ("fg", "muted", "accent", "err"):  # body text, secondary text, links, error text
        assert ratio(t[name], t["bg"]) >= 4.5, f"{theme}: --{name} {t[name]} on {t['bg']} = {ratio(t[name], t['bg']):.2f}"
    assert ratio(t["accent"], t["bg"]) >= 3.0  # the focus ring colour (non-text contrast)


def test_focus_is_visible_on_every_interactive_element_and_never_removed():
    rule = re.search(r"([^{}]*:focus-visible[^{}]*)\{([^}]*)\}", CSS)
    selectors, body = rule.group(1), rule.group(2)
    for sel in ("a:focus-visible", "button:focus-visible", "input:focus-visible", "select:focus-visible"):
        assert sel in selectors
    width = int(re.search(r"outline:\s*(\d+)px solid", body).group(1))
    assert width >= 2
    assert not re.search(r"outline:\s*(none|0)", CSS), "an outline is removed somewhere"
    assert re.search(r"\.skip:focus\s*\{[^}]*left:\s*1rem", CSS), "skip link must appear on focus"


def test_tap_targets_are_at_least_44px_and_text_scales():
    assert re.search(r"button, input, select \{[^}]*min-height:\s*2\.75rem", CSS)
    assert "font: 1rem" in CSS and "px" not in re.search(r"body \{([^}]*)\}", CSS).group(1)


def test_long_unbroken_text_can_wrap_on_a_phone():
    assert re.search(r"(overflow-wrap|word-break|word-wrap)\s*:\s*(anywhere|break-word|break-all)", CSS)
