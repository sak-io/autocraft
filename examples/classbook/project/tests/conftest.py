import pytest

from classbook.config import Settings
from classbook.kernel import db

GOOD_ENV = {
    "APP_ENV": "test",
    "ADMIN_EMAIL": "maya@example.com",
    "ADMIN_PASSWORD": "a-long-test-password-123",
}


@pytest.fixture
def env(tmp_path):
    return {**GOOD_ENV, "DATABASE_PATH": str(tmp_path / "t.db")}


@pytest.fixture
def settings(env):
    return Settings.from_env(env)


@pytest.fixture
def dbpath(tmp_path):
    """Real temp-file SQLite, migrated, with the production pragmas."""
    path = tmp_path / "t.db"
    db.migrate(path)
    return path


@pytest.fixture
def conn(dbpath):
    c = db.connect(dbpath)
    yield c
    c.close()


def add_user(conn, email="s@example.com", role="student"):
    return conn.execute(
        "INSERT INTO users (email, name, password_hash, role, created_at) VALUES (?, 'N', 'x', ?, '2026-01-01T00:00:00Z')",
        (email, role),
    ).lastrowid


def add_class(conn, starts="2026-11-01T10:00:00Z", capacity=2, status="active"):
    return conn.execute(
        "INSERT INTO classes (title, starts_at, duration_min, instructor, capacity, status, created_at) "
        "VALUES ('Flow', ?, 60, 'Maya', ?, ?, '2026-01-01T00:00:00Z')",
        (starts, capacity, status),
    ).lastrowid


def add_booking(conn, class_id, user_id, status="booked"):
    by = None if status == "booked" else "student"
    return conn.execute(
        "INSERT INTO bookings (class_id, user_id, status, cancelled_by, created_at) VALUES (?, ?, ?, ?, '2026-01-01T00:00:00Z')",
        (class_id, user_id, status, by),
    ).lastrowid
