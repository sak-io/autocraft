from datetime import datetime, timedelta, timezone

import pytest

from classbook.kernel import timeutil as t

UTC = timezone.utc


def test_text_roundtrip_is_utc_and_sortable():
    dt = datetime(2026, 10, 10, 18, 30, tzinfo=UTC)
    assert t.to_text(dt) == "2026-10-10T18:30:00Z"
    assert t.from_text("2026-10-10T18:30:00Z") == dt


def test_naive_datetimes_are_rejected():
    with pytest.raises(ValueError):
        t.to_text(datetime(2026, 1, 1))


def test_london_summer_and_winter_offsets():
    assert t.london_to_utc(datetime(2026, 7, 1, 12, 0)) == datetime(2026, 7, 1, 11, 0, tzinfo=UTC)
    assert t.london_to_utc(datetime(2026, 12, 1, 12, 0)) == datetime(2026, 12, 1, 12, 0, tzinfo=UTC)


def test_spring_forward_gap_is_rejected():
    # 2026-03-29: 01:00 -> 02:00, so 01:30 never happens
    with pytest.raises(t.NonexistentLocalTime):
        t.london_to_utc(datetime(2026, 3, 29, 1, 30))
    with pytest.raises(t.NonexistentLocalTime):
        t.london_to_utc(datetime(2026, 3, 29, 1, 0))


def test_times_just_around_the_gap_are_fine():
    assert t.london_to_utc(datetime(2026, 3, 29, 0, 59)) == datetime(2026, 3, 29, 0, 59, tzinfo=UTC)
    assert t.london_to_utc(datetime(2026, 3, 29, 2, 0)) == datetime(2026, 3, 29, 1, 0, tzinfo=UTC)


def test_autumn_fold_takes_first_occurrence():
    # 2026-10-25: 02:00 BST -> 01:00 GMT, so 01:30 happens twice; first = BST = 00:30Z
    assert t.london_to_utc(datetime(2026, 10, 25, 1, 30)) == datetime(2026, 10, 25, 0, 30, tzinfo=UTC)


def test_parse_london_input_formats_and_errors():
    expect = datetime(2026, 10, 10, 17, 30, tzinfo=UTC)
    assert t.parse_london_input("2026-10-10T18:30") == expect
    assert t.parse_london_input(" 2026-10-10 18:30 ") == expect
    for bad in ("", "tomorrow", "2026-13-01T10:00", "2026-10-10"):
        with pytest.raises(ValueError):
            t.parse_london_input(bad)
    with pytest.raises(t.NonexistentLocalTime):
        t.parse_london_input("2026-03-29T01:30")


def test_format_london_shows_local_time():
    assert t.format_london(datetime(2026, 7, 1, 11, 0, tzinfo=UTC)) == "Wed 01 Jul 2026, 12:00"


def test_clock_is_utc_and_whole_seconds_and_fixed_clock_moves():
    now = t.Clock().now()
    assert now.tzinfo is not None and now.microsecond == 0
    fc = t.FixedClock(datetime(2026, 1, 1, tzinfo=UTC))
    fc.advance(hours=1)
    assert fc.now() == datetime(2026, 1, 1, 1, tzinfo=UTC)
