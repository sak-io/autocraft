"""T7 (7): exploratory checks that need a real server process: broken clients, restarts, parallel sign-ups."""
import socket
from concurrent.futures import ThreadPoolExecutor

from tests.e2e.conftest import real_at, seed_students, sign_in
from tests.qa.support import PASSWORD, csrf_in, insert_class, insert_user, one, rows


def raw(port: int, payload: bytes, shutdown_write=True) -> bytes:
    with socket.create_connection(("127.0.0.1", port), timeout=10) as s:
        out = b""
        try:  # the server may (rightly) slam the door before we finish sending
            s.sendall(payload)
            if shutdown_write:
                s.shutdown(socket.SHUT_WR)
            while chunk := s.recv(65536):
                out += chunk
        except (ConnectionResetError, BrokenPipeError, OSError):
            pass
        return out


def status_line(resp: bytes) -> str:
    return resp.split(b"\r\n", 1)[0].decode("latin-1")


def test_server_survives_broken_and_hostile_clients_and_keeps_serving(live):
    server = live()
    p = server.port
    cases = {
        "not http": b"\x00\x01\x02garbage\r\n\r\n",
        "bad method": b"BREW /coffee HTTP/1.1\r\nHost: x\r\n\r\n",
        "no host http/1.1": b"GET / HTTP/1.1\r\n\r\n",
        "huge url": b"GET /" + b"a" * 200_000 + b" HTTP/1.1\r\nHost: x\r\n\r\n",
        "huge header": b"GET / HTTP/1.1\r\nHost: x\r\nCookie: " + b"a=" + b"b" * 200_000 + b"\r\n\r\n",
        "nul in path": b"GET /%00 HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n",
        "lying content-length": b"POST /login HTTP/1.1\r\nHost: x\r\nContent-Type: application/x-www-form-urlencoded\r\nContent-Length: 500\r\n\r\nemail=a",
        "negative content-length": b"POST /login HTTP/1.1\r\nHost: x\r\nContent-Length: -5\r\n\r\n",
        "two content-lengths": b"POST /login HTTP/1.1\r\nHost: x\r\nContent-Length: 3\r\nContent-Length: 4\r\n\r\nabcd",
        "chunked garbage": b"POST /login HTTP/1.1\r\nHost: x\r\nTransfer-Encoding: chunked\r\n\r\nZZZ\r\n",
        "oversize body": b"POST /login HTTP/1.1\r\nHost: x\r\nContent-Type: application/x-www-form-urlencoded\r\nContent-Length: 20000\r\nConnection: close\r\n\r\n" + b"a" * 20000,
    }
    for name, payload in cases.items():
        reply = raw(p, payload)
        line = status_line(reply)
        print(f"[T7] {name}: {line or '(connection closed)'}")
        assert line == "" or line.split()[1].startswith("4"), f"{name}: {line}"  # closed, or a 4xx: never a 5xx
    # the server is still healthy and logged no crash
    assert server.client().get("/health").json() == {"status": "ok"}
    assert "Traceback" not in server.log, server.log[-1500:]


def test_data_and_sessions_survive_a_server_restart(live, tmp_path):
    state = {}

    def seed(conn):
        state["tokens"], state["cid"] = seed_students(conn, 1, class_capacity=3)

    path = tmp_path / "persist.db"
    first = live(seed, path=path)
    c = first.client()
    c.cookies.set("session", state["tokens"][0])
    assert c.post_form(f"/classes/{state['cid']}/book").status_code == 303
    assert first.wait_for(lambda: one(path, "SELECT COUNT(*) FROM messages WHERE status='recorded'") == 1)
    first.proc.terminate()
    first.proc.wait(10)
    second = live(path=path)  # same file, new process: no in-memory state may be needed
    c2 = second.client()
    c2.cookies.set("session", state["tokens"][0])
    mine = c2.get("/my-bookings")
    assert mine.status_code == 200 and "Race Class" in mine.text
    assert one(path, "SELECT COUNT(*) FROM users WHERE role='admin'") == 1  # bootstrap did not duplicate the admin
    assert second.client().get("/").status_code == 200


def test_parallel_signups_with_one_email_create_exactly_one_account_and_no_errors(live):
    server = live()
    pages = [server.client() for _ in range(8)]
    tokens = [csrf_in(c.get("/signup").text) for c in pages]

    def go(i):
        return pages[i].post("/signup", data={"csrf_token": tokens[i], "name": f"Dup {i}", "email": "dup@example.com",
                                              "password": "another-password-1"}).status_code

    with ThreadPoolExecutor(8) as pool:
        statuses = sorted(pool.map(go, range(8)))
    assert statuses == [303] + [422] * 7, statuses
    assert one(server.path, "SELECT COUNT(*) FROM users WHERE email='dup@example.com'") == 1
    assert "Traceback" not in server.log


def test_login_lockout_over_real_http_is_per_email_and_ends_after_15_minutes_worth_of_state(live):
    def seed(conn):
        insert_user(conn, "locked@example.com", "Locked", password=PASSWORD)
        insert_user(conn, "free@example.com", "Free", password=PASSWORD)

    server = live(seed)
    c = server.client()
    form = c.get("/login")
    for _ in range(10):
        r = c.post("/login", data={"csrf_token": csrf_in(form.text), "email": "locked@example.com", "password": "wrong-wrong-wrong"})
        assert r.status_code == 401
    r = c.post("/login", data={"csrf_token": csrf_in(form.text), "email": "LOCKED@example.com", "password": PASSWORD})
    assert r.status_code == 429 and r.headers["retry-after"] == "900"          # even the right password, any letter case
    assert sign_in(server, "free@example.com", PASSWORD).get("/my-bookings").status_code == 200  # others are unaffected
    assert "Traceback" not in server.log and PASSWORD not in server.log
