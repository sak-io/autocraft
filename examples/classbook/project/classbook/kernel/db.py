"""SQLite access: fixed pragmas, write_tx() and the migration runner (ADR-0002).

Connections use isolation_level=None (autocommit) so Python never opens a hidden
transaction; write_tx() issues BEGIN IMMEDIATE itself, so waiting for the write
lock obeys busy_timeout. Read `now` once INSIDE write_tx (after the lock is held).
"""
from __future__ import annotations

import os
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .timeutil import Clock, to_text

BUSY_TIMEOUT_MS = 5000
MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"
_MIGRATION_RE = re.compile(r"^(\d{4})_[a-z0-9_]+\.sql$")


class DatabaseBusy(Exception):
    """The write lock could not be obtained within busy_timeout (answer 503)."""


class MigrationError(Exception):
    pass


def connect(path: str | os.PathLike, busy_timeout_ms: int = BUSY_TIMEOUT_MS) -> sqlite3.Connection:
    conn = sqlite3.connect(
        str(path), isolation_level=None, timeout=busy_timeout_ms / 1000, check_same_thread=False
    )
    conn.row_factory = sqlite3.Row
    conn.execute(f"PRAGMA busy_timeout = {int(busy_timeout_ms)}")
    conn.execute("PRAGMA journal_mode = WAL")  # needs a local disk
    conn.execute("PRAGMA synchronous = FULL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _is_busy(exc: sqlite3.OperationalError) -> bool:
    msg = str(exc).lower()
    return "locked" in msg or "busy" in msg


@contextmanager
def read_conn(path, busy_timeout_ms: int = BUSY_TIMEOUT_MS):
    conn = connect(path, busy_timeout_ms)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def write_tx(path, busy_timeout_ms: int = BUSY_TIMEOUT_MS):
    """BEGIN IMMEDIATE ... COMMIT (ROLLBACK on any exception). Raises DatabaseBusy on lock timeout."""
    conn = connect(path, busy_timeout_ms)
    try:
        try:
            conn.execute("BEGIN IMMEDIATE")
        except sqlite3.OperationalError as exc:
            if _is_busy(exc):
                raise DatabaseBusy("database is busy") from exc
            raise
        try:
            yield conn
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        else:
            conn.execute("COMMIT")
    finally:
        conn.close()


def _migration_files(directory: Path) -> list[tuple[int, Path]]:
    found = []
    for p in sorted(directory.glob("*.sql")):
        m = _MIGRATION_RE.match(p.name)
        if not m:
            raise MigrationError(f"bad migration file name: {p.name}")
        found.append((int(m.group(1)), p))
    versions = [v for v, _ in found]
    if versions != list(range(1, len(versions) + 1)):
        raise MigrationError("migrations must be numbered 0001, 0002, ... without gaps")
    return found


def migrate(path, migrations_dir: Path = MIGRATIONS_DIR, clock: Clock | None = None) -> list[int]:
    """Apply pending numbered SQL files in order, each in one transaction. Idempotent.

    Additive only. If the database already has data (an earlier version applied) and
    something is pending, a private copy `<db>.pre-v<N>.bak` is taken first.
    Returns the versions applied by this call.
    """
    clock = clock or Clock()
    files = _migration_files(Path(migrations_dir))
    conn = connect(path)
    applied_now: list[int] = []
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_version "
            "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
        current = conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_version").fetchone()[0]
        if current > len(files):
            raise MigrationError("database is newer than this program; refusing to start")
        pending = [(v, p) for v, p in files if v > current]
        if pending and current > 0:
            bak = f"{path}.pre-v{pending[0][0]:04d}.bak"
            if os.path.exists(bak):
                os.remove(bak)
            conn.execute("VACUUM INTO ?", (bak,))
            os.chmod(bak, 0o600)  # contains personal data
        for version, file in pending:
            script = file.read_text(encoding="utf-8")
            stamp = to_text(clock.now())
            try:
                conn.executescript(
                    "BEGIN IMMEDIATE;\n" + script + "\n"
                    f"INSERT INTO schema_version (version, applied_at) VALUES ({version}, '{stamp}');\n"
                    "COMMIT;"
                )
            except Exception as exc:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                raise MigrationError(f"migration {file.name} failed: {type(exc).__name__}") from exc
            applied_now.append(version)
    finally:
        conn.close()
    return applied_now
