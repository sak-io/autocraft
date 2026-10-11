from datetime import datetime, timedelta, timezone

from classbook.kernel import rules
from classbook.kernel.timeutil import london_to_utc, to_london, to_text
from tests.conftest import add_booking, add_class, add_user

UTC = timezone.utc
NOW = datetime(2026, 10, 10, 12, 0, 0, tzinfo=UTC)
S = timedelta(seconds=1)


def cls(start, status="active"):
    return {"starts_at": to_text(start), "status": status}


# --- 30-day booking window (exact boundaries) ---
def test_bookable_exactly_30x24h_ahead():
    assert rules.is_bookable(cls(NOW + timedelta(days=30)), NOW)


def test_not_bookable_one_second_beyond_30_days():
    assert not rules.is_bookable(cls(NOW + timedelta(days=30) + S), NOW)


def test_bookable_one_second_inside_30_days():
    assert rules.is_bookable(cls(NOW + timedelta(days=30) - S), NOW)


def test_not_bookable_when_started_or_starting_now():
    assert not rules.is_bookable(cls(NOW), NOW)
    assert not rules.is_bookable(cls(NOW - S), NOW)
    assert rules.is_bookable(cls(NOW + S), NOW)


def test_cancelled_class_is_never_bookable():
    assert not rules.is_bookable(cls(NOW + timedelta(days=1), "cancelled"), NOW)


def test_label_disappears_exactly_at_opens_at_without_admin_action():
    c = cls(NOW + timedelta(days=35))
    opens = rules.opens_at(c)
    assert opens == NOW + timedelta(days=5)
    assert not rules.is_bookable(c, opens - S)
    assert rules.is_bookable(c, opens)  # day 30 exactly: Book appears


def test_thirty_by_24h_across_autumn_dst_change():
    # Class at 09:00 London on 2026-10-26 (GMT, after the 25 Oct clock change).
    start = london_to_utc(datetime(2026, 10, 26, 9, 0))
    c = cls(start)
    opens = rules.opens_at(c)
    assert opens == start - timedelta(hours=720)
    # 720 hours earlier is 09:00Z = 10:00 BST, NOT 09:00 local (calendar-day arithmetic)
    assert to_london(opens).strftime("%d %H:%M") == "26 10:00"
    assert rules.is_bookable(c, opens)
    assert not rules.is_bookable(c, opens - S)


def test_thirty_by_24h_across_spring_dst_change():
    # Class 09:00 London on 2026-04-05 (BST = 08:00Z); 30 days back crosses 29 Mar.
    start = london_to_utc(datetime(2026, 4, 5, 9, 0))
    c = cls(start)
    opens = rules.opens_at(c)
    assert opens == start - timedelta(hours=720)
    assert to_london(opens).strftime("%d %H:%M") == "06 08:00"  # 6 Mar, one hour earlier locally
    assert rules.is_bookable(c, opens) and not rules.is_bookable(c, opens - S)


# --- 60-day listing horizon ---
def test_listing_horizon_is_60_days_and_excludes_started_and_cancelled():
    assert rules.is_listed(cls(NOW + timedelta(days=60)), NOW)
    assert not rules.is_listed(cls(NOW + timedelta(days=60) + S), NOW)
    assert rules.is_listed(cls(NOW + timedelta(days=45)), NOW)  # greyed but listed (AC-1.2)
    assert not rules.is_listed(cls(NOW), NOW)
    assert not rules.is_listed(cls(NOW + timedelta(days=1), "cancelled"), NOW)


# --- 12h cancellation cutoff ---
def test_cancel_allowed_exactly_12h():
    assert rules.cancel_allowed(cls(NOW + timedelta(hours=12)), NOW)


def test_cancel_refused_one_second_inside_12h():
    assert not rules.cancel_allowed(cls(NOW + timedelta(hours=12) - S), NOW)


def test_cancel_allowed_one_second_beyond_12h():
    assert rules.cancel_allowed(cls(NOW + timedelta(hours=12) + S), NOW)


def test_cancel_refused_when_started():
    assert not rules.cancel_allowed(cls(NOW), NOW)
    assert not rules.cancel_allowed(cls(NOW - timedelta(hours=1)), NOW)


def test_rules_accept_datetime_starts_and_sqlite_rows(conn):
    assert rules.is_bookable({"starts_at": NOW + timedelta(days=1), "status": "active"}, NOW)
    cid = add_class(conn, to_text(NOW + timedelta(days=1)))
    row = conn.execute("SELECT * FROM classes WHERE id=?", (cid,)).fetchone()
    assert rules.is_bookable(row, NOW)


# --- spots left (derived, never stored) ---
def test_spots_left_counts_only_booked(conn):
    cid = add_class(conn, capacity=3)
    u1, u2 = add_user(conn, "a@x.io"), add_user(conn, "b@x.io")
    assert rules.spots_left(conn, cid) == 3
    add_booking(conn, cid, u1)
    add_booking(conn, cid, u2, status="cancelled")
    assert rules.spots_left(conn, cid) == 2
    assert rules.spots_left(conn, 999) is None


def test_spots_left_sql_fragment_usable_in_listing(conn):
    cid = add_class(conn, capacity=2)
    add_booking(conn, cid, add_user(conn))
    row = conn.execute(f"SELECT {rules.SPOTS_LEFT_SQL} AS n FROM classes c WHERE c.id=?", (cid,)).fetchone()
    assert row["n"] == 1
