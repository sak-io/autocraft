"""Clock, UTC <-> Europe/London conversion and parsing (architecture s3, "Time rules").

Instants are stored as UTC text in a fixed, sortable format: 2026-10-10T14:30:00Z.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

LONDON = ZoneInfo("Europe/London")
UTC = timezone.utc
_STORE_FMT = "%Y-%m-%dT%H:%M:%SZ"


class NonexistentLocalTime(ValueError):
    """The London local time falls in the spring-forward gap and never happens."""


class Clock:
    """Source of 'now'. Production uses this class; tests use FixedClock."""

    def now(self) -> datetime:
        return datetime.now(UTC).replace(microsecond=0)


class FixedClock(Clock):
    def __init__(self, now: datetime):
        self._now = ensure_utc(now)

    def now(self) -> datetime:
        return self._now

    def set(self, now: datetime) -> None:
        self._now = ensure_utc(now)

    def advance(self, **delta) -> None:
        self._now += timedelta(**delta)


def ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError("naive datetime: an aware datetime is required")
    return dt.astimezone(UTC).replace(microsecond=0)


def to_text(dt: datetime) -> str:
    """Aware datetime -> stored UTC text."""
    return ensure_utc(dt).strftime(_STORE_FMT)


def from_text(value: str | datetime) -> datetime:
    """Stored UTC text (or an already aware datetime) -> aware UTC datetime."""
    if isinstance(value, datetime):
        return ensure_utc(value)
    return datetime.strptime(value, _STORE_FMT).replace(tzinfo=UTC)


def london_to_utc(local: datetime) -> datetime:
    """Naive London wall-clock time -> aware UTC.

    Gap (clocks go forward, the time does not exist): NonexistentLocalTime.
    Fold (clocks go back, the time happens twice): the first occurrence.
    """
    if local.tzinfo is not None:
        raise ValueError("expected a naive London wall-clock time")
    first = local.replace(tzinfo=LONDON, fold=0)
    utc = first.astimezone(UTC)
    if utc.astimezone(LONDON).replace(tzinfo=None) != local:
        raise NonexistentLocalTime("that local time does not exist in London (clocks go forward)")
    return utc.replace(microsecond=0)


def parse_london_input(text: str) -> datetime:
    """Admin form value 'YYYY-MM-DDTHH:MM' (or with a space) -> aware UTC.

    Raises ValueError (bad format) or NonexistentLocalTime.
    """
    text = text.strip()
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"):
        try:
            local = datetime.strptime(text, fmt)
            break
        except ValueError:
            continue
    else:
        raise ValueError("expected a date and time like 2026-10-10 18:30")
    return london_to_utc(local)


def to_london(dt: datetime) -> datetime:
    return ensure_utc(dt).astimezone(LONDON)


def format_london(dt: datetime) -> str:
    """For display, e.g. 'Sat 10 Oct 2026, 18:30'."""
    return to_london(dt).strftime("%a %d %b %Y, %H:%M")
