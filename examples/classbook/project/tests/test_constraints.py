import sqlite3

import pytest

from tests.conftest import add_booking, add_class, add_user


def test_capacity_zero_and_negative_rejected(conn):
    for cap in (0, -1):
        with pytest.raises(sqlite3.IntegrityError):
            add_class(conn, capacity=cap)


def test_duplicate_active_booking_rejected_but_rebooking_after_cancel_allowed(conn):
    cid, uid = add_class(conn), add_user(conn)
    first = add_booking(conn, cid, uid)
    with pytest.raises(sqlite3.IntegrityError):
        add_booking(conn, cid, uid)
    conn.execute("UPDATE bookings SET status='cancelled', cancelled_by='student', cancelled_at='x' WHERE id=?", (first,))
    add_booking(conn, cid, uid)  # new row after a cancel
    add_booking(conn, cid, uid, status="cancelled")  # many cancelled rows are fine
    assert conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0] == 3


def test_second_admin_rejected(conn):
    add_user(conn, "admin@x.io", "admin")
    with pytest.raises(sqlite3.IntegrityError):
        add_user(conn, "other@x.io", "admin")
    add_user(conn, "stud1@x.io")
    add_user(conn, "stud2@x.io")  # many students are fine


def test_email_unique_and_lowercase(conn):
    add_user(conn, "a@x.io")
    with pytest.raises(sqlite3.IntegrityError):
        add_user(conn, "a@x.io")
    with pytest.raises(sqlite3.IntegrityError):
        add_user(conn, "Upper@x.io")


@pytest.mark.parametrize("sql", [
    "INSERT INTO users (email,name,password_hash,role,created_at) VALUES ('r@x.io','n','h','owner','t')",
    "INSERT INTO classes (title,starts_at,duration_min,instructor,capacity,status,created_at) VALUES ('t','s',60,'i',1,'weird','t')",
])
def test_enum_checks(conn, sql):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(sql)


def test_cancelled_by_is_set_exactly_when_cancelled(conn):
    cid, uid = add_class(conn), add_user(conn)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO bookings (class_id,user_id,status,cancelled_by,created_at) VALUES (?,?,'booked','student','t')", (cid, uid))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO bookings (class_id,user_id,status,cancelled_by,created_at) VALUES (?,?,'cancelled',NULL,'t')", (cid, uid))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO bookings (class_id,user_id,status,cancelled_by,created_at) VALUES (?,?,'cancelled','nobody','t')", (cid, uid))
    conn.execute("INSERT INTO bookings (class_id,user_id,status,cancelled_by,created_at) VALUES (?,?,'cancelled','studio','t')", (cid, uid))


def test_foreign_keys_enforced(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO bookings (class_id,user_id,created_at) VALUES (999,999,'t')")


def test_message_unique_per_booking_and_kind(conn):
    bid = add_booking(conn, add_class(conn), add_user(conn))
    ins = "INSERT INTO messages (to_email,subject,body,kind,booking_id,created_at) VALUES ('a@x.io','s','b',?,?,'t')"
    conn.execute(ins, ("booked", bid))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(ins, ("booked", bid))
    conn.execute(ins, ("cancelled", bid))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO messages (to_email,subject,body,kind,status,created_at) VALUES ('a','s','b','k','sent','t')")


def test_sessions_and_user_actions_cascade_with_user(conn):
    uid = add_user(conn)
    conn.execute("INSERT INTO sessions VALUES ('h', ?, 't', 't')", (uid,))
    conn.execute("INSERT INTO user_actions (user_id, at) VALUES (?, 't')", (uid,))
    conn.execute("DELETE FROM users WHERE id=?", (uid,))
    assert conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM user_actions").fetchone()[0] == 0


def test_login_failures_table_exists_and_is_writable(conn):
    conn.execute("INSERT INTO login_failures (key, at) VALUES ('email:a@x.io', '2026-01-01T00:00:00Z')")
