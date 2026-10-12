"""Booking and cancellation rules (T5). Rule order is fixed by api.md #6 and #8.

Every function runs ONE write transaction and reads `now` exactly once INSIDE it, after the lock is held
(architecture s3). It RETURNS what happened as a `Result`, so the caller (T6) sends mail only for
BOOKED / CANCELLED, after the commit. Refusals are normal returns, not exceptions: the attempt row in
`user_actions` must be committed even when the request is refused (F24: refusals count).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from ..kernel import db, rules
from ..kernel.timeutil import Clock, from_text, to_text

ACTION_CAP = 20  # book/cancel attempts per user per rolling hour
ACTION_WINDOW = timedelta(hours=1)


class Outcome(str, Enum):
    BOOKED = "booked"
    ALREADY_BOOKED = "already_booked"          # no-op
    CANCELLED = "cancelled"
    ALREADY_CANCELLED = "already_cancelled"    # no-op
    NOT_FOUND = "not_found"                    # unknown class / not your booking -> 404
    STARTED_OR_CANCELLED = "started_or_cancelled"
    TOO_FAR_AHEAD = "too_far_ahead"
    FULL = "full"
    TOO_LATE = "too_late"
    THROTTLED = "throttled"


@dataclass(frozen=True)
class Result:
    outcome: Outcome
    booking_id: int | None = None
    class_id: int | None = None
    class_title: str | None = None
    starts_at: datetime | None = None
    user_email: str | None = None
    user_name: str | None = None
    opens_at: datetime | None = None   # set for TOO_FAR_AHEAD
    now: datetime | None = None

    @property
    def changed(self) -> bool:
        """True only for a real new booking / cancellation: the only cases that send an email."""
        return self.outcome in (Outcome.BOOKED, Outcome.CANCELLED)


def _admit(conn, user_id: int, now: datetime) -> bool:
    """Count this attempt against the hourly cap. False (and nothing recorded) when the cap is reached."""
    since = to_text(now - ACTION_WINDOW)
    used = conn.execute(
        "SELECT COUNT(*) FROM user_actions WHERE user_id = ? AND at > ?", (user_id, since)
    ).fetchone()[0]
    if used >= ACTION_CAP:
        return False
    conn.execute("INSERT INTO user_actions (user_id, at) VALUES (?, ?)", (user_id, to_text(now)))
    return True


def _user(conn, user_id: int):
    return conn.execute("SELECT email, name FROM users WHERE id = ?", (user_id,)).fetchone()


def book(db_path, clock: Clock, user_id: int, class_id: int) -> Result:
    """Order: cap -> unknown -> started/cancelled -> too far ahead -> already booked (no-op) -> full."""
    with db.write_tx(db_path) as conn:
        now = clock.now()  # the one clock read, after BEGIN IMMEDIATE has been granted
        if not _admit(conn, user_id, now):
            return Result(Outcome.THROTTLED, class_id=class_id, now=now)
        cls = conn.execute("SELECT * FROM classes WHERE id = ?", (class_id,)).fetchone()
        if cls is None:
            return Result(Outcome.NOT_FOUND, class_id=class_id, now=now)
        base = dict(class_id=cls["id"], class_title=cls["title"], starts_at=from_text(cls["starts_at"]), now=now)
        if cls["status"] != "active" or rules.starts_at(cls) <= now:
            return Result(Outcome.STARTED_OR_CANCELLED, **base)
        if not rules.is_bookable(cls, now):
            return Result(Outcome.TOO_FAR_AHEAD, opens_at=rules.opens_at(cls), **base)
        existing = conn.execute(
            "SELECT id FROM bookings WHERE class_id = ? AND user_id = ? AND status = 'booked'", (class_id, user_id)
        ).fetchone()
        if existing:
            return Result(Outcome.ALREADY_BOOKED, booking_id=existing["id"], **base)
        if rules.spots_left(conn, class_id) <= 0:
            return Result(Outcome.FULL, **base)
        u = _user(conn, user_id)
        booking_id = conn.execute(
            "INSERT INTO bookings (class_id, user_id, status, created_at) VALUES (?, ?, 'booked', ?)",
            (class_id, user_id, to_text(now)),
        ).lastrowid
        return Result(Outcome.BOOKED, booking_id=booking_id, user_email=u["email"], user_name=u["name"], **base)


def cancel(db_path, clock: Clock, user_id: int, booking_id: int) -> Result:
    """Order: cap -> not found or not mine -> already cancelled (no-op) -> too late."""
    with db.write_tx(db_path) as conn:
        now = clock.now()
        if not _admit(conn, user_id, now):
            return Result(Outcome.THROTTLED, booking_id=booking_id, now=now)
        row = conn.execute(  # ownership in SQL: user_id comes from the session only
            "SELECT b.id, b.status, c.id AS class_id, c.title, c.starts_at, c.status AS class_status "
            "FROM bookings b JOIN classes c ON c.id = b.class_id WHERE b.id = ? AND b.user_id = ?",
            (booking_id, user_id),
        ).fetchone()
        if row is None:
            return Result(Outcome.NOT_FOUND, booking_id=booking_id, now=now)
        base = dict(booking_id=row["id"], class_id=row["class_id"], class_title=row["title"],
                    starts_at=from_text(row["starts_at"]), now=now)
        if row["status"] != "booked":
            return Result(Outcome.ALREADY_CANCELLED, **base)
        if not rules.cancel_allowed(row, now):
            return Result(Outcome.TOO_LATE, **base)
        u = _user(conn, user_id)
        conn.execute(
            "UPDATE bookings SET status = 'cancelled', cancelled_by = 'student', cancelled_at = ? "
            "WHERE id = ? AND status = 'booked'",
            (to_text(now), booking_id),
        )
        return Result(Outcome.CANCELLED, user_email=u["email"], user_name=u["name"], **base)


def upcoming_for(conn, user_id: int, now: datetime) -> list[dict]:
    """My bookings: own upcoming booked rows plus those cancelled by the studio (F18). Student-cancelled rows
    are not shown. Ownership is in the SQL."""
    rows = conn.execute(
        "SELECT b.id, b.status, c.id AS class_id, c.title, c.instructor, c.starts_at, c.duration_min "
        "FROM bookings b JOIN classes c ON c.id = b.class_id "
        "WHERE b.user_id = ? AND c.starts_at > ? AND (b.status = 'booked' OR b.cancelled_by = 'studio') "
        "ORDER BY c.starts_at, b.id",
        (user_id, to_text(now)),
    ).fetchall()
    return [dict(r) for r in rows]
