import sqlite3

import pytest

from classbook.kernel import db

TABLES = {"users", "sessions", "classes", "bookings", "messages", "login_failures", "user_actions", "schema_version"}


def tables(path):
    c = sqlite3.connect(path)
    try:
        return {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        c.close()


def test_empty_database_gets_full_schema(tmp_path):
    p = tmp_path / "a.db"
    assert db.migrate(p) == [1]
    assert TABLES <= tables(p)


def test_migrate_is_idempotent(tmp_path):
    p = tmp_path / "a.db"
    db.migrate(p)
    assert db.migrate(p) == []
    assert db.migrate(p) == []
    c = sqlite3.connect(p)
    assert c.execute("SELECT COUNT(*) FROM schema_version").fetchone()[0] == 1
    c.close()


def test_upgrade_path_keeps_data_and_takes_backup(tmp_path):
    mig = tmp_path / "mig"
    mig.mkdir()
    real = (db.MIGRATIONS_DIR / "0001_initial.sql").read_text()
    (mig / "0001_initial.sql").write_text(real)
    p = tmp_path / "a.db"
    assert db.migrate(p, mig) == [1]
    with db.write_tx(p) as c:
        c.execute("INSERT INTO users (email,name,password_hash,role,created_at) VALUES ('a@x.io','A','h','student','2026-01-01T00:00:00Z')")
    # an additive second migration arrives later
    (mig / "0002_add_note.sql").write_text("ALTER TABLE classes ADD COLUMN note TEXT;")
    assert not (tmp_path / "a.db.pre-v0002.bak").exists()
    assert db.migrate(p, mig) == [2]
    assert (tmp_path / "a.db.pre-v0002.bak").exists()
    with db.read_conn(p) as c:
        assert c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
        assert "note" in [r["name"] for r in c.execute("PRAGMA table_info(classes)")]
    # the backup is the pre-migration state
    b = sqlite3.connect(tmp_path / "a.db.pre-v0002.bak")
    assert "note" not in [r[1] for r in b.execute("PRAGMA table_info(classes)")]
    assert b.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
    b.close()


def test_fresh_database_takes_no_backup(tmp_path):
    db.migrate(tmp_path / "a.db")
    assert not list(tmp_path.glob("*.bak"))


def test_failed_migration_rolls_back_and_is_not_recorded(tmp_path):
    mig = tmp_path / "mig"
    mig.mkdir()
    (mig / "0001_ok.sql").write_text("CREATE TABLE a (x INTEGER);")
    (mig / "0002_bad.sql").write_text("CREATE TABLE b (x INTEGER); INSERT INTO nope VALUES (1);")
    p = tmp_path / "a.db"
    with pytest.raises(db.MigrationError):
        db.migrate(p, mig)
    assert "b" not in tables(p) and "a" in tables(p)
    c = sqlite3.connect(p)
    assert [r[0] for r in c.execute("SELECT version FROM schema_version")] == [1]
    c.close()


def test_database_newer_than_program_refuses(tmp_path):
    p = tmp_path / "a.db"
    db.migrate(p)
    c = sqlite3.connect(p)
    c.execute("INSERT INTO schema_version VALUES (2, 'x')")
    c.commit()
    c.close()
    with pytest.raises(db.MigrationError):
        db.migrate(p)


def test_bad_migration_names_and_gaps_rejected(tmp_path):
    (tmp_path / "x.sql").write_text("")
    with pytest.raises(db.MigrationError):
        db.migrate(tmp_path / "a.db", tmp_path)
    (tmp_path / "x.sql").unlink()
    (tmp_path / "0002_late.sql").write_text("")
    with pytest.raises(db.MigrationError):
        db.migrate(tmp_path / "a.db", tmp_path)


def test_connections_use_the_production_pragmas(conn):
    one = lambda q: conn.execute(q).fetchone()[0]
    assert one("PRAGMA journal_mode") == "wal"
    assert one("PRAGMA synchronous") == 2  # FULL
    assert one("PRAGMA foreign_keys") == 1
    assert one("PRAGMA busy_timeout") == 5000
    assert conn.isolation_level is None
