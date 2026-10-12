import json
import logging

import pytest
from fastapi.testclient import TestClient

from classbook.app import create_app
from classbook.config import Settings
from classbook.kernel import db
from classbook.logging_setup import JsonFormatter, log, request_id_var


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as c:
        yield c


def test_health_ok_and_migrates_on_startup(client, settings):
    r = client.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}
    with db.read_conn(settings.database_path) as c:
        assert c.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] == 1


def test_health_503_when_database_unreachable(settings, monkeypatch):
    app = create_app(settings)
    def boom(*a, **k):
        raise RuntimeError("disk gone /secret/path")
    monkeypatch.setattr(db, "read_conn", boom)
    r = TestClient(app).get("/health")
    assert r.status_code == 503 and r.json() == {"status": "unavailable"}


def test_creating_the_app_twice_is_safe(settings):
    create_app(settings)
    create_app(settings)


def test_creates_missing_database_directory(tmp_path, env):
    env["DATABASE_PATH"] = str(tmp_path / "nested" / "dir" / "c.db")
    create_app(Settings.from_env(env))
    assert (tmp_path / "nested" / "dir" / "c.db").exists()


def test_request_id_header_is_unique_per_request(client):
    a, b = client.get("/health"), client.get("/health")
    assert a.headers["x-request-id"] != b.headers["x-request-id"]


def test_unhandled_exception_gives_generic_500_and_logged_with_request_id(settings, capfd):
    app = create_app(settings)

    @app.get("/boom")
    def boom():
        raise ValueError("leaky detail: password=hunter2 token=abc123")

    r = TestClient(app, raise_server_exceptions=False).get("/boom?token=abc123")
    assert r.status_code == 500
    rid = r.headers["x-request-id"]
    assert rid in r.text and "Something went wrong" in r.text
    assert "hunter2" not in r.text and "ValueError" not in r.text and "Traceback" not in r.text

    out = capfd.readouterr().out
    lines = [json.loads(l) for l in out.splitlines() if l.startswith("{")]
    err = [l for l in lines if l["msg"] == "unhandled exception"]
    assert len(err) == 1 and err[0]["request_id"] == rid and err[0]["exc_type"] == "ValueError"
    assert any(f.endswith(" boom") for f in err[0]["frames"])  # stack location is logged
    # no secrets: not the exception message, not the query string, not config secrets
    for secret in ("hunter2", "abc123", settings.admin_password):
        assert secret not in out
    access = [l for l in lines if l["msg"] == "request" and l["path"] == "/boom"]
    assert access[0]["status"] == 500 and access[0]["request_id"] == rid


def test_database_busy_answers_503_page(settings):
    app = create_app(settings)

    @app.get("/busy")
    def busy():
        raise db.DatabaseBusy("x")

    r = TestClient(app).get("/busy")
    assert r.status_code == 503 and r.headers["retry-after"] == "5"


def test_log_lines_are_one_json_object_with_redacted_sensitive_fields():
    rec = logging.LogRecord("classbook", logging.INFO, "f", 1, "hello", None, None)
    rec.fields = {"password": "p", "Set-Cookie": "c", "session_id": "s", "csrf_token": "t", "user_id": 7}
    request_id_var.set("rid123")
    line = JsonFormatter().format(rec)
    obj = json.loads(line)
    assert "\n" not in line and obj["request_id"] == "rid123" and obj["user_id"] == 7
    assert {obj[k] for k in ("password", "Set-Cookie", "session_id", "csrf_token")} == {"[redacted]"}
    request_id_var.set("-")


def test_bad_config_makes_startup_fail_fast_without_secrets(monkeypatch, capsys):
    monkeypatch.setattr("os.environ", {"ADMIN_EMAIL": "maya@example.com", "ADMIN_PASSWORD": "short-secret"})
    with pytest.raises(SystemExit) as e:
        create_app()
    assert e.value.code == 1
    assert "short-secret" not in capsys.readouterr().err
