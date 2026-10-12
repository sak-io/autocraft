"""The booking rules, in exactly one place (architecture s3/s4).

`cls` is anything indexable by 'starts_at' (UTC text or aware datetime) and
'status', e.g. a sqlite3.Row or a dict. All comparisons use the caller's single
`now` (read once, after the write lock is held).
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

from .timeutil import from_text

# "30 days" is exactly 30 x 24 hours, never calendar days, so DST cannot move it.
BOOKING_WINDOW = timedelta(days=30)
LISTING_HORIZON = timedelta(days=60)  # LISTING_HORIZON_DAYS=60 (assumption, arch s11)
CANCEL_CUTOFF = timedelta(hours=12)

# SQL expression (needs the classes table aliased as `c`): never stored, always derived.
SPOTS_LEFT_SQL = (
    "(c.capacity - (SELECT COUNT(*) FROM bookings b "
    "WHERE b.class_id = c.id AND b.status = 'booked'))"
)


def starts_at(cls) -> datetime:
    return from_text(cls["starts_at"])


def is_bookable(cls, now: datetime) -> bool:
    """Active and now < starts_at <= now + 30x24h. The single 30-day predicate."""
    return cls["status"] == "active" and now < starts_at(cls) <= now + BOOKING_WINDOW


def opens_at(cls) -> datetime:
    """Instant booking opens: starts_at - 30x24h."""
    return starts_at(cls) - BOOKING_WINDOW


def is_listed(cls, now: datetime) -> bool:
    """Shown on the schedule: active and now < starts_at <= now + 60 days."""
    return cls["status"] == "active" and now < starts_at(cls) <= now + LISTING_HORIZON


def cancel_allowed(cls, now: datetime) -> bool:
    """A student may cancel iff starts_at - now >= 12h (exactly 12h is allowed)."""
    return starts_at(cls) - now >= CANCEL_CUTOFF


def spots_left(conn: sqlite3.Connection, class_id: int) -> int | None:
    """capacity - booked bookings, or None for an unknown class."""
    row = conn.execute(
        f"SELECT {SPOTS_LEFT_SQL} AS left FROM classes c WHERE c.id = ?", (class_id,)
    ).fetchone()
    return None if row is None else row[0]
