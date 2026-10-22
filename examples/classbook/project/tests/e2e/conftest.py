"""Real HTTP: the app runs as a separate `uvicorn` process exactly like the Dockerfile CMD (one worker,
--no-proxy-headers), against a real temp-file SQLite database with the production pragmas. Tests talk to it
with httpx and look at the database file and the process log afterwards.
"""
import os
import socket
import subprocess
import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from classbook.auth import service
from classbook.kernel import db
from classbook.kernel.timeutil import to_text
from tests.qa.support import ADMIN_EMAIL, ADMIN_PASSWORD, Browser, insert_class, insert_user

ROOT = Path(__file__).resolve().parents[2]


def real_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def real_at(**delta) -> str:
    return to_text(real_now() + timedelta(**delta))


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class LiveServer:
    def __init__(self, proc, port, path, lines):
        self.proc, self.port, self.path, self.lines = proc, port, path, lines
        self.url = f"http://127.0.0.1:{port}"

    def client(self, **kw) -> Browser:
        return Browser(base_url=self.url, timeout=30, **kw)

    @property
    def log(self) -> str:
        return "\n".join(self.lines)

    def wait_for(self, condition, timeout=15.0):
        """Poll a DB condition (e.g. 'the background email has been recorded') with a hard deadline."""
        gate, waited = threading.Event(), 0.0
        while waited < timeout:
            if condition():
                return True
            gate.wait(0.02)
            waited += 0.02
        return condition()


@pytest.fixture
def live(tmp_path):
    """live(seed=callable(conn), env={...}) -> LiveServer. The seed runs on a migrated DB BEFORE start."""
    started: list[LiveServer] = []

    def start(seed=None, env=None, path=None) -> LiveServer:
        path = path or tmp_path / f"live{len(started)}.db"
        db.migrate(path)
        if seed:
            conn = db.connect(path)
            conn.execute("BEGIN")
            seed(conn)
            conn.execute("COMMIT")
            conn.close()
        port = free_port()
        child_env = {k: v for k, v in os.environ.items() if not k.startswith(("APP_", "ADMIN_", "DATABASE_", "MAIL_", "TRUSTED_"))}
        child_env.update({"APP_ENV": "development", "DATABASE_PATH": str(path), "ADMIN_EMAIL": ADMIN_EMAIL,
                          "ADMIN_PASSWORD": ADMIN_PASSWORD, "TRUSTED_PROXY_HOPS": "0",
                          "PYTHONPATH": str(ROOT), "PYTHONUNBUFFERED": "1", **(env or {})})
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "--factory", "classbook.app:create_app", "--host", "127.0.0.1",
             "--port", str(port), "--workers", "1", "--no-access-log", "--no-proxy-headers"],
            cwd=ROOT, env=child_env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        lines: list[str] = []
        ready = threading.Event()

        def pump():
            for line in proc.stdout:
                lines.append(line.rstrip())
                if "Application startup complete" in line:
                    ready.set()
            ready.set()  # process ended: unblock the waiter, which then fails with the log

        threading.Thread(target=pump, daemon=True).start()
        assert ready.wait(60) and proc.poll() is None, "server did not start:\n" + "\n".join(lines)
        server = LiveServer(proc, port, path, lines)
        started.append(server)
        return server

    yield start
    for server in started:
        server.proc.terminate()
        try:
            server.proc.wait(10)
        except subprocess.TimeoutExpired:
            server.proc.kill()


def seed_students(conn, n, class_capacity=1, starts_in_days=3, title="Race Class", password=None):
    """n students (ids 1..n) each with a live session token; one class. Returns (tokens, class_id)."""
    now = real_now()
    tokens = []
    for i in range(n):
        uid = insert_user(conn, f"s{i}@example.com", f"Student {i}", password=password)
        tokens.append(service.create_session(conn, uid, now))
    cid = insert_class(conn, real_at(days=starts_in_days), class_capacity, title)
    return tokens, cid


def sign_in(server, email, password, next=None):
    """A real sign-in through the form: the server's own CSRF cookie and field. Returns the signed-in client."""
    from tests.qa.support import csrf_in
    client = server.client()
    page = client.get("/login" + (f"?next={next}" if next else ""))
    resp = client.post("/login", data={"csrf_token": csrf_in(page.text), "email": email, "password": password,
                                       **({"next": next} if next else {})})
    assert resp.status_code == 303, resp.text[:300]
    return client
