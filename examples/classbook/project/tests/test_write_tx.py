import threading
import time

import pytest

from classbook.kernel import db
from tests.conftest import add_class


def test_commits_on_success_and_rolls_back_on_error(dbpath):
    with db.write_tx(dbpath) as c:
        add_class(c)
    with pytest.raises(RuntimeError):
        with db.write_tx(dbpath) as c:
            add_class(c)
            raise RuntimeError("boom")
    with db.read_conn(dbpath) as c:
        assert c.execute("SELECT COUNT(*) FROM classes").fetchone()[0] == 1


def test_write_tx_waits_on_a_held_lock_instead_of_failing_at_once(dbpath):
    """Held for ~1s; a plain deferred read-then-write would fail instantly with 'database is locked'."""
    holding, release = threading.Event(), threading.Event()

    def holder():
        with db.write_tx(dbpath) as c:
            add_class(c, "2026-11-01T10:00:00Z")
            holding.set()
            release.wait(5)

    t = threading.Thread(target=holder)
    t.start()
    assert holding.wait(5)
    threading.Timer(1.0, release.set).start()
    started = time.monotonic()
    with db.write_tx(dbpath) as c:  # default busy_timeout 5000
        waited = time.monotonic() - started
        assert c.execute("SELECT COUNT(*) FROM classes").fetchone()[0] == 1  # sees the holder's commit
        add_class(c, "2026-11-02T10:00:00Z")
    t.join()
    assert 0.8 <= waited < 4.5, waited
    with db.read_conn(dbpath) as c:
        assert c.execute("SELECT COUNT(*) FROM classes").fetchone()[0] == 2


def test_lock_timeout_raises_database_busy(dbpath):
    holding, release = threading.Event(), threading.Event()

    def holder():
        with db.write_tx(dbpath) as c:
            holding.set()
            release.wait(5)

    t = threading.Thread(target=holder)
    t.start()
    assert holding.wait(5)
    started = time.monotonic()
    with pytest.raises(db.DatabaseBusy):
        with db.write_tx(dbpath, busy_timeout_ms=300):
            pass
    assert 0.25 <= time.monotonic() - started < 3
    release.set()
    t.join()


def test_readers_are_not_blocked_by_a_writer_in_wal(dbpath):
    with db.write_tx(dbpath) as w:
        add_class(w)
        with db.read_conn(dbpath, busy_timeout_ms=100) as r:
            assert r.execute("SELECT COUNT(*) FROM classes").fetchone()[0] == 0  # uncommitted not visible


def test_serialised_counter_under_contention_has_no_lost_updates(dbpath):
    with db.write_tx(dbpath) as c:
        c.execute("CREATE TABLE ctr (n INTEGER)")
        c.execute("INSERT INTO ctr VALUES (0)")

    def bump():
        with db.write_tx(dbpath) as c:
            n = c.execute("SELECT n FROM ctr").fetchone()[0]  # read-then-write
            c.execute("UPDATE ctr SET n = ?", (n + 1,))

    threads = [threading.Thread(target=bump) for _ in range(20)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    with db.read_conn(dbpath) as c:
        assert c.execute("SELECT n FROM ctr").fetchone()[0] == 20
