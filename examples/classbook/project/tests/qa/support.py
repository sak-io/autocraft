"""Shared helpers for the T7 cross-task tests.

Unlike the per-task tests these use REAL sessions (no dependency overrides): users are rows, sessions are made
with the production `create_session`, so the whole stack (cookie -> session lookup -> guard -> service -> SQL)
is exercised. CSRF uses the real double-submit: any well-formed token works as long as cookie == form field.
"""
from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from classbook.app import create_app
from classbook.auth import service
from classbook.auth.passwords import hash_password
from classbook.config import Settings
from classbook.kernel import db
from classbook.kernel.timeutil import FixedClock, to_text

NOW = datetime(2026, 10, 10, 12, 0, 0, tzinfo=timezone.utc)
TOKEN = "Q" * 43  # a well-formed CSRF token; cookie and form field carry the same value
ADMIN_EMAIL, ADMIN_PASSWORD = "maya@example.com", "a-long-admin-password-123"
PASSWORD = "correct horse battery staple"


def at(**delta) -> str:
    return to_text(NOW + timedelta(**delta))


def env_for(path) -> dict:
    return {"APP_ENV": "test", "DATABASE_PATH": str(path), "ADMIN_EMAIL": ADMIN_EMAIL,
            "ADMIN_PASSWORD": ADMIN_PASSWORD}


def insert_user(conn, email, name="Student", role="student", password=None) -> int:
    pw = hash_password(password) if password else "x"  # "x" can never verify: session-only user
    return conn.execute(
        "INSERT INTO users (email, name, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)",
        (email, name, pw, role, at())).lastrowid


def insert_class(conn, starts, capacity=2, title="Flow", instructor="Maya", status="active", duration=60) -> int:
    return conn.execute(
        "INSERT INTO classes (title, starts_at, duration_min, instructor, capacity, status, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)", (title, starts, duration, instructor, capacity, status, at())).lastrowid


def insert_booking(conn, class_id, user_id, status="booked", by=None) -> int:
    by = by or (None if status == "booked" else "student")
    return conn.execute(
        "INSERT INTO bookings (class_id, user_id, status, cancelled_by, cancelled_at, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)", (class_id, user_id, status, by, at() if by else None, at())).lastrowid


def rows(path, sql, *params):
    conn = db.connect(path)
    try:
        return [tuple(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def one(path, sql, *params):
    return rows(path, sql, *params)[0][0]


def session_for(path, user_id, clock_now=NOW) -> str:
    with db.write_tx(path) as conn:
        return service.create_session(conn, user_id, clock_now)


class Browser(httpx.Client):
    """httpx client that never follows redirects and posts forms with a matching CSRF cookie/field."""

    def __init__(self, *args, **kw):
        kw.setdefault("follow_redirects", False)
        super().__init__(*args, **kw)

    def post_form(self, path, data=None, csrf=True, **kw):
        data = dict(data or {})
        if csrf:
            self.cookies.delete("csrf")  # pages the server rendered may have set their own token cookie
            self.cookies.set("csrf", TOKEN)
            data["csrf_token"] = TOKEN
        return self.post(path, data=data, **kw)


class AppBrowser(TestClient, Browser):  # TestClient (in-process ASGI) with the same helpers
    def __init__(self, app, **kw):
        kw.setdefault("follow_redirects", False)
        TestClient.__init__(self, app, **kw)


def location(resp) -> str:
    return resp.headers["location"]


def csrf_in(html: str) -> str:
    return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)


@dataclass
class World:
    path: Path
    settings: Settings
    clock: FixedClock
    app: object
    ids: dict

    def browser(self, who: str | None) -> AppBrowser:
        """who: None (anonymous), 'a', 'b' (students) or 'admin'."""
        b = AppBrowser(self.app)
        if who:
            b.cookies.set("session", session_for(self.path, self.ids[who], self.clock.now()))
        return b


def build_template(tmp_path) -> Path:
    """Migrated DB with: admin (bootstrap), students a and b, class 1 (3 days out, capacity 2, A booked),
    class 2 (far: 45 days), class 3 (cancelled)."""
    path = tmp_path / "template.db"
    settings = Settings.from_env(env_for(path))
    create_app(settings, FixedClock(NOW))  # migrates + bootstraps the one admin (id 1)
    conn = db.connect(path)
    conn.execute("BEGIN")
    a = insert_user(conn, "a@example.com", "Alice A")
    b = insert_user(conn, "b@example.com", "Bob B")
    c1 = insert_class(conn, at(days=3), 2, "Flow")
    c2 = insert_class(conn, at(days=45), 5, "Far Yoga")
    c3 = insert_class(conn, at(days=4), 5, "Cancelled Class", status="cancelled")
    bk = insert_booking(conn, c1, a)
    conn.execute("COMMIT")
    conn.close()
    build_template.ids = dict(admin=1, a=a, b=b, c1=c1, c2=c2, c3=c3, booking_a=bk)
    return path


def copy_world(template: Path, tmp_path, name="w") -> World:
    path = tmp_path / f"{name}.db"
    shutil.copy(template, path)
    for ext in ("-wal", "-shm"):
        if Path(str(template) + ext).exists():
            shutil.copy(str(template) + ext, str(path) + ext)
    settings = Settings.from_env(env_for(path))
    clock = FixedClock(NOW)
    app = create_app(settings, clock)
    return World(path, settings, clock, app, dict(build_template.ids))
