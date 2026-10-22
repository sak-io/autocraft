"""Sessions, throttles and "last sign-in" data. SQL is parameterised; callers hash outside write_tx."""
from __future__ import annotations

import hashlib
import re
import secrets
from datetime import datetime, timedelta

from ..kernel.timeutil import to_text

SESSION_DAYS = 14
LOGIN_WINDOW = timedelta(minutes=15)
EMAIL_FAIL_CAP, IP_FAIL_CAP = 10, 20
SIGNUP_WINDOW, SIGNUP_CAP = timedelta(hours=1), 10
KEEP_FAILURES = timedelta(days=1)
KEEP_ACTIONS = timedelta(days=1)  # the booking cap counts the last hour only
KEEP_MESSAGES = timedelta(days=90)
_TOKEN = re.compile(r"^[A-Za-z0-9_-]{43}$")  # token_urlsafe(32)


def email_key(email: str) -> str:
    return "email:" + email.strip().lower()[:254]


def ip_key(ip: str) -> str:
    return "ip:" + ip[:64]


def signup_key(ip: str) -> str:
    return "signup:" + ip[:64]


def count_since(conn, key: str, since: datetime) -> int:
    return conn.execute("SELECT COUNT(*) FROM login_failures WHERE key = ? AND at > ?",
                        (key, to_text(since))).fetchone()[0]


def login_throttled(conn, email: str, ip: str, now: datetime) -> bool:
    since = now - LOGIN_WINDOW
    return count_since(conn, email_key(email), since) >= EMAIL_FAIL_CAP or count_since(conn, ip_key(ip), since) >= IP_FAIL_CAP


def signup_throttled(conn, ip: str, now: datetime) -> bool:
    return count_since(conn, signup_key(ip), now - SIGNUP_WINDOW) >= SIGNUP_CAP


def record(conn, keys: list[str], now: datetime) -> None:
    conn.executemany("INSERT INTO login_failures (key, at) VALUES (?, ?)", [(k, to_text(now)) for k in keys])


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def well_formed(token: str | None) -> bool:
    return bool(token) and _TOKEN.match(token) is not None


def create_session(conn, user_id: int, now: datetime) -> str:
    """New random token (never reuses a presented one); returns the cookie value, stores only its hash."""
    token = secrets.token_urlsafe(32)
    conn.execute("INSERT INTO sessions (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
                 (token_hash(token), user_id, to_text(now), to_text(now + timedelta(days=SESSION_DAYS))))
    return token


def delete_session(conn, token: str | None) -> None:
    if well_formed(token):
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash(token),))


def mark_sign_in(conn, user_id: int, now: datetime) -> None:
    conn.execute("UPDATE users SET prev_login_at = last_login_at, last_login_at = ? WHERE id = ?", (to_text(now), user_id))


def session_user(conn, token: str | None, now: datetime):
    """Row (id, email, name, role) for a live session, else None (forged, expired, logged out)."""
    if not well_formed(token):
        return None
    return conn.execute(
        "SELECT u.id, u.email, u.name, u.role FROM sessions s JOIN users u ON u.id = s.user_id "
        "WHERE s.token_hash = ? AND s.expires_at > ?", (token_hash(token), to_text(now))).fetchone()


def purge_expired(conn, now: datetime) -> None:
    conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (to_text(now),))
    conn.execute("DELETE FROM login_failures WHERE at <= ?", (to_text(now - KEEP_FAILURES),))
    conn.execute("DELETE FROM user_actions WHERE at <= ?", (to_text(now - KEEP_ACTIONS),))
    conn.execute("DELETE FROM messages WHERE created_at <= ?", (to_text(now - KEEP_MESSAGES),))


def last_sign_in(conn, user_id: int) -> dict:
    """For the admin page (T4): previous successful sign-in and failed attempts on this email since then."""
    row = conn.execute("SELECT email, prev_login_at FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        return {"previous": None, "failures_since": 0}
    prev = row["prev_login_at"]
    n = conn.execute("SELECT COUNT(*) FROM login_failures WHERE key = ? AND at > ?",
                     (email_key(row["email"]), prev or "")).fetchone()[0]
    return {"previous": prev, "failures_since": n}
